import contextlib
import os
import pathlib
from typing import Any, Callable, Generic, Optional, TypeVar, Union, final

from ._context import (
    CatchSpec,
    current_module_mylang_counterpart,
    change_context_var,
    current_stack_frame,
    nested_stack_frame,
    LexicalScope,
    StackFrame,
)
from ._utils import (
    currently_called_func,
    expose,
    function_defined_as_class,
    getattr_,
    getname,
    isinstance_,
    python_dict_from_args_kwargs,
    python_obj_to_mylang,
    set_contextvar,
    FunctionAsClass,
    populate_locals_for_callable,
    expose_instance_attr,
    is_attr_exposed,
)
from .base import Args, Array, Dict, IncompleteExpression, Object, TypedObject
from .complex import Path, String
from .error import Error, ErrorCarrier

__all__ = ("fun", "call", "get", "set_")


TypeReturn = TypeVar("TypeReturn", bound=Object)


class _Symbols:
    CURRENT_EXPORT = type("CURRENT_EXPORT", (object,), {})
    """The object that will be exported from the current module."""


@expose
@function_defined_as_class
@expose_instance_attr("name", "parameters", "body")
class fun(Object, FunctionAsClass, Generic[TypeReturn]):
    _CLASSCALL_SHOULD_RECEIVE_NEW_STACK_FRAME = False
    _CALL_SHOULD_RECEIVE_NEW_STACK_FRAME = True

    def __init__(self, name: Object, /, *parameters_and_body: Object, **kwargs):
        # When somebody constructs fun(...), Python will run __init__ automatically. Since we already called it from
        # _m_classcall_, another call should do nothing
        if currently_called_func.get() is None:
            return

        parameters_and_body = (
            parameters_and_body if isinstance(parameters_and_body, Args) else Args(*parameters_and_body)
        )
        parameters = Args(*parameters_and_body[:-1]) + Args.from_dict(parameters_and_body.keyed_dict()) + Args(**kwargs)
        body = parameters_and_body[-1]
        assert isinstance(body, StatementList), "Body must be a StatementList"
        self.name = python_obj_to_mylang(name)
        self.parameters = parameters
        self.body = body
        self.closure_lexical_scope = self.__class__._caller_lexical_scope()
        """The lexical scope in which this function was defined."""
        self.__class__._caller_locals()[name] = self

    @classmethod
    def _m_classcall_(cls, args: "Args", /):
        # TODO: Args must have unique names
        func = super().__new__(cls)
        func.__init__(
            args[0],
            Args(*args[1:]) + Args.from_dict(args.keyed_dict()),
        )
        return func

    def _m_call_(self, args: Args, /) -> TypeReturn:
        stack_frame = current_stack_frame.get()
        stack_frame.set_parent_lexical_scope(self.closure_lexical_scope)
        populate_locals_for_callable(stack_frame.locals, self.parameters, args)
        return self.body.execute()

    def __repr__(self):
        return f"{self.__class__.__name__}({self.name!r})"

    def _m_repr_(self):
        return String(f"{{fun {self.name.value!r}}}")


@expose
@function_defined_as_class(monkeypatch_methods=False)
class call(Object, FunctionAsClass):
    _CLASSCALL_SHOULD_RECEIVE_NEW_STACK_FRAME = False

    def __new__(cls, func_key, *args, **kwargs):
        with (
            set_contextvar(current_stack_frame, StackFrame())
            if current_stack_frame.get() is None
            else contextlib.nullcontext()
        ):
            if isinstance(func_key, Args):
                if len(args) > 0 or len(kwargs) > 0:
                    raise ValueError("If the first argument is of type Args, no other arguments are allowed.")
                return cls._m_classcall_(func_key)
            elif len(args) > 0 and isinstance(mylang_args := args[0], Args):
                if len(args) > 1:
                    raise ValueError("If an argument of type Args is used, it must be the only argument.")
                return cls._m_classcall_([func_key] + mylang_args)
            else:
                return cls._m_classcall_(
                    Args.from_dict(python_dict_from_args_kwargs(func_key, *args, **kwargs)),
                )

    def __init__(self, func_key, *args, **kwargs):
        super().__init__(func_key, *args, **kwargs)

    @classmethod
    def _m_classcall_(cls, args: Args, /):
        func_key, rest = args[0], args[1:]

        # `call` is special, it operates in the caller's stack frame
        caller_stack_frame = cls._caller_stack_frame()

        obj_to_call: Object
        if isinstance(_ref := func_key, ref):
            obj_to_call = _ref.obj
        else:
            with set_contextvar(currently_called_func, get._m_classcall_):
                obj_to_call = get._m_classcall_(Args(func_key))

        needs_new_stack_frame = True

        if isinstance(obj_to_call, type) and issubclass(obj_to_call, FunctionAsClass):
            # Function defined as class
            python_callable = obj_to_call._m_classcall_
            needs_new_stack_frame = obj_to_call._CLASSCALL_SHOULD_RECEIVE_NEW_STACK_FRAME
        else:
            # Regular MyLang callable
            python_callable = obj_to_call._m_call_

        with (
            set_contextvar(currently_called_func, python_callable),
            nested_stack_frame() if needs_new_stack_frame else contextlib.nullcontext(),
        ):
            fun_args = Args.from_positional_keyed(rest, args.keyed_dict())
            try:
                value = python_callable(fun_args)
                return value
            except Exception as e:
                if isinstance(e, ErrorCarrier):
                    e = e.error

                catch_spec = caller_stack_frame.catch_spec
                if catch_spec is not None:
                    caller_stack_frame.catch_spec = None
                    result = cls.__process_caught_error(e, catch_spec)
                    if result is not None:
                        return result
                    else:
                        # No catch clause matched the type of the error
                        raise
                else:
                    raise

    @classmethod
    def __process_caught_error(cls, e: Error | Exception, catch_spec: CatchSpec) -> Optional[Object]:
        """Process a caught error according to the given catch specification.

        If an error type matches, execute the corresponding body and return its
        value. If no error type matches, return None.
        """
        any_error_matched = False
        caller_stack_frame = cls._caller_stack_frame()

        @python_obj_to_mylang
        def execute_if_error_matches(*args: Object):
            """When called with args `[key1, key2, ...] body`, look up each key in the
            lexical scope, and if it resolves to an error type that `e` is an
            instance of, execute `body`.
            """
            for key in args[:-1]:
                current_stack_frame.get().set_parent_lexical_scope(caller_stack_frame.lexical_scope)

                # Check if the error matches the error clause
                # Treat Python's regular Exception as equivalent to MyLang's Error
                # If a regular Exception has made its way here, it must be a bug
                error_type = get(key)
                if isinstance(e, Exception):
                    does_match = error_type is Error
                else:
                    does_match = isinstance_(e, error_type)

                if does_match:
                    nonlocal any_error_matched
                    any_error_matched = True
                    original_body: StatementList = args[-1]
                    if catch_spec.error_key is not None:
                        # Inject the error into the catch body, under the specified key
                        body = StatementList.from_iterable([
                            Args.from_dict({
                                0: ref.of(set_),
                                catch_spec.error_key: (
                                    e
                                    if isinstance(e, Object)
                                    else Error("TODO: Opaque error")
                                ),
                            }),
                            *original_body,
                        ])
                    else:
                        body = original_body

                    catch_body.aborted = True
                    return body.execute()

        catch_body = StatementList.from_iterable(
            (Args(ref.of(execute_if_error_matches)) + args for args in catch_spec.body)
        )
        value = catch_body.execute()

        if any_error_matched:
            return value
        else:
            return None


@expose
@function_defined_as_class
class get(Object, FunctionAsClass):
    _CLASSCALL_SHOULD_RECEIVE_NEW_STACK_FRAME = False

    @classmethod
    def _m_classcall_(cls, args: Args, /):
        # TODO: Proper exception type
        assert len(args) == 1, "get function requires exactly one argument"
        if isinstance(args[0], ref):
            return args[0].obj

        parts = args[0].parts if isinstance(args[0], Path) else (args[0],)

        obj = cls._caller_lexical_scope()

        for part in parts:
            obj = getattr_(obj, part)

        return obj


@expose
@function_defined_as_class
class set_(Object, FunctionAsClass):
    _CLASSCALL_SHOULD_RECEIVE_NEW_STACK_FRAME = False
    _m_name_ = "set"

    @classmethod
    def _m_classcall_(cls, args: Args, /):
        from .primitive import undefined

        lexical_scope_locals = cls._caller_lexical_scope().locals
        for key, value in args._m_dict_.items():
            obj = lexical_scope_locals
            if isinstance(key, Path):
                for part in key.parts[:-1]:
                    obj = getattr_(obj, part)
                last_key = key.parts[-1]
            else:
                last_key = key

            if isinstance(obj, TypedObject):
                obj._m_dict_[last_key] = value
            else:
                obj[last_key] = value

        return undefined


@expose
@function_defined_as_class
class use(Object, FunctionAsClass):
    """Use code from another file.

    The use function is MyLang's module import system. It loads and executes
    code from external sources (files or standard library modules) and makes
    the exported functionality available in the current scope.

    Supports loading:
    - Standard library modules
    - Third-party MyLang modules
    - TODO: URLs, relative/absolute paths

    Features:
    - Module caching for performance
    - Integration with MyLang's export system
    - TODO: Automatic module resolution
    """

    _CLASSCALL_SHOULD_RECEIVE_NEW_STACK_FRAME = False

    __cache: dict[str, Object] = {}
    """Cache of loaded modules to avoid reloading. Keys are cache IDs, values are exported objects."""

    def __init__(self, source: str, /, *, use_cache=True):
        """Specifies the call contract.
        Args:
            source: The module source identifier (string or path)
            use_cache: Whether to use cached modules (default: True)
        """
        super().__init__(source, use_cache=use_cache)

    @classmethod
    def _m_classcall_(cls, args: Args, /):
        """Execute the use function to import a module.

        This is the main entry point for the use function. It validates arguments,
        determines the appropriate loader, handles caching, and binds the imported
        module to the caller's scope.

        Args: See __init__

        Returns:
            The exported value from the loaded module

        Raises:
            ValueError: If incorrect number of arguments provided
            NotImplementedError: If source is not a String or Path
            TypeError: If use_cache is not a Bool
        """
        from .complex import String

        # TODO: Generalize validation based on __init__ function signature

        # Prepare variables
        if len(args[:]) != 1:
            raise ValueError("use requires exactly one positional argument")

        if not isinstance(source := args[0], (String, Path)):
            raise NotImplementedError("use requires a String or Path as the first argument")

        use_cache = True
        if "use_cache" in args:
            use_cache = args["use_cache"]
            from .primitive import Bool

            if not isinstance(use_cache, Bool):
                raise TypeError("use_cache must be a Bool")

        if isinstance(source, (String, Path)):
            loader: Callable[[Any], Object] = cls.loaders.lookup
        else:
            assert False, "Unreachable"

        # Look up in cache and return if found
        cache_id = cls._get_cache_id(source, loader)

        if use_cache and cache_id in use.__cache:
            # Return cached value if available
            exported_value = use.__cache[cache_id]

            cls._caller_locals()[args[0]] = exported_value
            return exported_value

        # Evaluate the module
        exported_value = loader(source)
        # TODO: Modify to work with Path
        # Bind the exported value in the caller's context
        cls._caller_locals()[source] = exported_value
        # Store in cache
        use.__cache[cache_id] = exported_value

        return exported_value

    @classmethod
    def _set_alias_binding_in_caller_context(cls, name: "String", exported_value: Object):
        """Set the alias binding in the caller's lexical scope.

        This method binds an imported module under an alias name in the caller's
        local scope, making it accessible for use.

        Args:
            name: The alias name to bind the module under
            exported_value: The module's exported value to bind
        """
        set_(Args.from_dict({name: exported_value}))

    @classmethod
    def _get_cache_id(cls, source, loader):
        """Generate a unique (hashable) cache identifier for a module."""
        return (source, loader)

    @classmethod
    def _load_mylang_module(cls, code: str):
        """Load and execute a MyLang module from source code.

        Parse the code, transform it into executable statements, and execute
        the module in a nested stack frame with builtins injected.

        Args:
            code: The MyLang source code to execute

        Returns:
            A tuple of (exported_value, lexical_scope) where:
            - exported_value: The module's exported value (return value or exported dict)
            - lexical_scope: The module's lexical scope for further manipulation
        """
        from ...parser import parser
        from ...transformer import Transformer
        from .. import builtins_

        tree = parser.parse(code, start="module")

        # Enter a nested context, execute the module and obtain its exported
        # value. The exported value is either a dict of the module's locals or a
        # specific return value if return was called from within.
        exported_value: Object

        # Inject builtins
        stack_frame = current_stack_frame.get()
        stack_frame.set_parent_lexical_scope(LexicalScope(builtins_.create_locals_dict()))
        statement_list = Transformer().transform(tree)
        statement_list.execute()

        if stack_frame.return_value is not None:
            exported_value = stack_frame.return_value
        else:
            # TODO: Maybe wrap in a module type?
            # TODO: Use identity instead of hashing dict
            exported_value = stack_frame.lexical_scope.custom_data.pop(_Symbols.CURRENT_EXPORT, Dict())

        return exported_value, stack_frame.lexical_scope

    @classmethod
    def _load_mylang_file(cls, path: str):
        """Load and execute a MyLang module from a file.

        Reads the file content and delegates to _load_mylang_module for execution.

        Args:
            path: File system path to the .my file to load

        Returns:
            A tuple of (exported_value, lexical_scope) as returned by _load_mylang_module
        """
        with open(path, "r") as f:
            code = f.read()
        return cls._load_mylang_module(code)

    class loaders:
        """Contains loader delegates that are used based on the type of source.

        The loaders determine which loading strategy to use for different types
        of modules (standard library vs third-party).
        """

        class lookup:
            """Factory class that determines the appropriate loader for a given source."""

            def __init__(self, source: Union[String, Path]):
                _ = source

            def __new__(cls, source: Union[String, Path]):
                """Determine and return the appropriate loader for the source.

                Resolution order:
                1. Check if it's a Python module in stdlib
                2. Check if it's a MyLang .my file in stdlib
                3. Fall back to third-party loader

                Args:
                    source: The module source (String or Path)

                Returns:
                    An appropriate loader instance (std or third_party)
                """
                if isinstance(source, Path):
                    assert all(isinstance(part, String) for part in source.parts), "All parts of a Path must be String"

                import importlib.util

                spec = importlib.util.find_spec(f"..{source}", package=__package__)
                if spec:
                    return cls.std(source)
                else:
                    path = cls._get_mylang_module_in_stdlib(source)
                    if path.is_file():
                        return cls.std(source)
                    return cls.third_party(source)

            @classmethod
            def std(cls, source: Union[String, Path]) -> Object:
                """Load a standard library module (MyLang .my file or Python module).

                First attempts to load a MyLang .my file, then tries to import a
                corresponding Python module from the stdlib. Combines their exports
                if both exist.

                Args:
                    source: The module URI to load from stdlib

                Returns:
                    The returned value from the loaded module(s)

                Raises:
                    AssertionError: If the module is not found in stdlib
                """
                # Try a .my file in the standard library
                exported_value: Object | None = None
                file_path = cls._get_mylang_module_in_stdlib(source)
                lexical_scope: LexicalScope | None = None
                if file_path.is_file():
                    exported_value, lexical_scope = use._load_mylang_file(file_path)
                # Then try to import a Python module from the MyLang standard library
                import importlib

                with change_context_var(
                    current_module_mylang_counterpart,
                    exported_value,
                ):
                    try:
                        module = importlib.import_module(f"..{source}", package=__package__)
                        if exported_value is not None:
                            assert isinstance(exported_value, Dict), f"{file_path} did not export a Dict. Cannot import python file mylang.stdlib.{source}"

                            if lexical_scope is not None:
                                lexical_scope.locals[String("python")] = exported_value

                            # Add all globals from module which have been exposed using the expose decorator
                            for name, obj in vars(module).items():
                                if is_attr_exposed(module, name):
                                    mylang_obj = python_obj_to_mylang(obj)
                                    exported_value[name] = mylang_obj
                        else:
                            exported_value = python_obj_to_mylang(module)
                    except ModuleNotFoundError:
                        pass

                if exported_value is None:
                    assert False, f"Standard library module {source} not found."

                return exported_value

            @classmethod
            def third_party(cls, source: Union[String, Path]) -> Object:
                """Load a third-party MyLang module using lookup strategy.

                TODO: Currently looks up only in CWD.

                Loads external .my files that are not part of the standard library.
                Currently only supports String sources (not Path objects).

                Args:
                    source: The module name (must be a String)

                Returns:
                    The value returned from the loaded module
                """
                if not isinstance(source, String):
                    raise NotImplementedError("Third party modules can only be imported by String for now")
                if isinstance(source, String):
                    fpath = source.value + ".my"
                else:
                    fpath = os.path.join(*(part._m_str_().value for part in source.parts)) + ".my"
                return use._load_mylang_file(fpath)[0]

            @classmethod
            def _get_mylang_module_in_stdlib(cls, source: Union[String, Path]) -> pathlib.Path:
                """Get the file path for a MyLang module in the standard library.

                Constructs the full path to a .my file in the stdlib directory.

                Args:
                    source: The module name (String or Path)

                Returns:
                    pathlib.Path object pointing to the .my file in stdlib
                """
                stdlib_root = pathlib.Path(__file__).parent.parent
                if isinstance(source, Path):
                    subpath = os.path.join(*(part._m_str_().value for part in source.parts)) + ".my"
                else:
                    subpath = source.value + ".my"

                return stdlib_root / subpath


class StatementList(Array[Args]):
    def __init__(self, *args, **kwargs):
        self.aborted = False
        """Used by executed code to signal that the execution of the StatementList should be aborted."""
        super().__init__(*args, **kwargs)

    def execute(self) -> Object:
        from . import undefined

        for i_statement, statement in enumerate(self):
            result: Object
            # Make sure an expression is converted to Args. If already Args, it
            # won't be modified
            args = Args(statement)
            args = IncompleteExpression.evaluate_all_in_object(args)

            if args.is_keyed_only():
                result = set_(args)
            else:
                result = call(args)

            stack_frame = current_stack_frame.get()

            if stack_frame.return_value is not None:
                # If a return value was set, we stop executing further statements
                return stack_frame.return_value

            if i_statement == len(self) - 1:
                return result

            if self.aborted:
                return stack_frame.return_value or undefined

        return undefined

    def _m_repr_(self):
        from .complex import String

        return String("{" + type(self).__name__ + " " + str(super()._m_repr_()) + "}")


class ExecutionBlock(StatementList, IncompleteExpression):
    def evaluate(self) -> Object:
        caller_stack_frame = current_stack_frame.get()
        with nested_stack_frame() as stack_frame:
            stack_frame.set_parent_lexical_scope(caller_stack_frame.lexical_scope)
            return super().execute()


@expose
@function_defined_as_class
@final
class ref(Object, FunctionAsClass):
    _CLASSCALL_SHOULD_RECEIVE_NEW_STACK_FRAME = False

    def __init__(self, key: Object):
        # FIXME: For some reason `ref 1` doesn't throw, even though I didn't
        # explicitly assign set 1=...

        self.obj = self._caller_stack_frame()[key]

    @classmethod
    def of(cls, obj: Object, /):
        """Create a reference to an object."""
        instance = super().__new__(cls)
        if isinstance(obj, ref):
            obj = obj.obj
        instance.obj = obj
        return instance

    @classmethod
    def _m_classcall_(cls, args: Args, /):
        self = super().__new__(ref)
        key = args[0]
        self.__init__(key)
        return self

    def __str__(self):
        return f"{self.__class__.__name__}.of({self.obj})"

    def __repr__(self):
        return f"{self.__class__.__name__}.of({repr(self.obj)})"

    def _m_str_(self):
        return self.obj._m_str_()

    def _m_repr_(self):
        return self.obj._m_repr_()


@expose
@function_defined_as_class
@final
class op(Object, FunctionAsClass):
    """Invoke an operation by given operator in Polish notation."""

    _CLASSCALL_SHOULD_RECEIVE_NEW_STACK_FRAME = True

    from ._operators import operators

    # TODO: Make the operation functions first class citizens
    operators = operators

    def __init__(self, *args):
        super().__init__(*args)

    @classmethod
    def _m_classcall_(cls, args: Args, /):
        # TODO: Validate args
        return op.operators[str(args[0])](*args[1:])


@expose
@function_defined_as_class
class export(Object, FunctionAsClass):
    """Marker class to indicate that an attribute should be exported from a module."""

    _CLASSCALL_SHOULD_RECEIVE_NEW_STACK_FRAME = False

    def __init__(self, obj: Object):
        self.obj = obj

    @classmethod
    def _m_classcall_(self, args, /):
        positional = args[:]
        keyed = args.keyed_dict()

        lexical_scope = current_stack_frame.get().lexical_scope

        container_of_exports = lexical_scope.custom_data.get(_Symbols.CURRENT_EXPORT, None)
        if container_of_exports is None:
            container_of_exports = Dict()
            lexical_scope.custom_data[_Symbols.CURRENT_EXPORT] = container_of_exports

        for obj in positional:
            name = getname(obj)
            assert name is not None, f"Cannot export object {obj!r} as a positional argument without a name"
            container_of_exports[name] = obj

        for key, obj in keyed.items():
            container_of_exports[key] = obj

import contextlib
from typing import Generic, TypeVar, final

from ._context import (
    LocalsDict,
    current_stack_frame,
    nested_stack_frame,
    LexicalScope,
    StackFrame,
)
from ._utils import (
    Special,
    currently_called_func,
    expose,
    function_defined_as_class,
    getattr_,
    is_attr_exposed,
    python_dict_from_args_kwargs,
    python_obj_to_mylang,
    set_contextvar,
    FunctionAsClass, populate_locals_for_callable,
)
from .base import Args, Array, Dict, IncompleteExpression, Object, TypedObject
from .complex import Path, String

__all__ = ("fun", "call", "get", "set_")


TypeReturn = TypeVar("TypeReturn", bound=Object)


@expose
@function_defined_as_class
class fun(Object, FunctionAsClass, Generic[TypeReturn]):
    _CLASSCALL_SHOULD_RECEIVE_NEW_STACK_FRAME = False

    def __init__(self, name: Object, /, *parameters_and_body: Object, **kwargs):
        # When somebody constructs fun(...), Python will run __init__ automatically. Since we already called it from
        # _m_classcall_, another call should do nothing
        if currently_called_func.get() is None:
            return

        parameters_and_body = parameters_and_body if isinstance(parameters_and_body, Args) else Args(*parameters_and_body)
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
    @Special._m_classcall_
    def _m_classcall_(cls, args: "Args", /):
        # TODO: Args must have unique names
        func = super().__new__(cls)
        func.__init__(
            args[0],
            Args(*args[1:]) + Args.from_dict(args.keyed_dict()),
        )
        return func

    @Special._m_call_
    def _m_call_(self, args: Args, /) -> TypeReturn:
        stack_frame = current_stack_frame.get()
        stack_frame.set_parent_lexical_scope(self.closure_lexical_scope)
        populate_locals_for_callable(stack_frame.locals, self.parameters, args)
        return self.body.execute()

    def __repr__(self):
        return f"{self.__class__.__name__}({self.name!r})"

    @Special._m_repr_
    def _m_repr_(self):
        return String(f"fun {self.name!r}")

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
                    raise ValueError(
                        "If the first argument is of type Args, no other arguments are allowed."
                    )
                return cls._m_classcall_(func_key)
            elif len(args) > 0 and isinstance(mylang_args := args[0], Args):
                if len(args) > 1:
                    raise ValueError(
                        "If an argument of type Args is used, it must be the only argument."
                    )
                return cls._m_classcall_([func_key] + mylang_args)
            else:
                return cls._m_classcall_(
                    Args.from_dict(
                        python_dict_from_args_kwargs(func_key, *args, **kwargs)
                    ),
                )

    def __init__(self, func_key, *args, **kwargs):
        super().__init__(func_key, *args, **kwargs)

    @classmethod
    @Special._m_classcall_
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
            (
                nested_stack_frame()
                if needs_new_stack_frame
                else contextlib.nullcontext()
            ),
        ):
            fun_args = Args.from_positional_keyed(rest, args.keyed_dict())
            value = python_callable(fun_args)
            return value


@expose
@function_defined_as_class
class get(Object, FunctionAsClass):
    _CLASSCALL_SHOULD_RECEIVE_NEW_STACK_FRAME = False

    @classmethod
    @Special._m_classcall_
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
    _m_name_ = Special._m_name_("set")

    @classmethod
    @Special._m_classcall_
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
    """Use code from another file."""
    _CLASSCALL_SHOULD_RECEIVE_NEW_STACK_FRAME = False

    __cache: dict[str, Object] = {}

    def __init__(self, source: str, /, *, use_cache=True):
        super().__init__(source, use_cache=use_cache)

    @classmethod
    @Special._m_classcall_
    def _m_classcall_(cls, args: Args, /):
        from .complex import String

        # TODO: Generalize validation based on __init__ function signature

        if len(args[:]) != 1:
            raise ValueError("use requires exactly one positional argument")

        if not isinstance(args[0], String):
            raise TypeError("use requires a String as the first argument")

        use_cache = True
        if "use_cache" in args:
            use_cache = args["use_cache"]
            from .primitive import Bool

            if not isinstance(use_cache, Bool):
                raise TypeError("use_cache must be a Bool")

        # TODO: Use something more advanced
        unique_id = args[0].value

        if use_cache and unique_id in use.__cache:
            # Return cached value if available
            exported_value = use.__cache[args[0].value]

            cls._caller_locals()[args[0]] = exported_value
            return exported_value

        # TODO: Use a lookup strategy
        # TODO: Support Path in addition to String
        from ...parser import STATEMENT_LIST, parser
        from ...transformer import Transformer

        # TODO: File extension
        with open(args[0].value + ".my", "r") as f:
            code = f.read()
        tree = parser.parse(code, start=STATEMENT_LIST)

        # Enter a nested context, execute the module and obtain its exported
        # value The exported value is either a dict of the module's locals or a
        # specific return value if return was called from within.
        exported_value: Object
        with nested_stack_frame() as stack_frame:
            Transformer().transform(tree)

            if stack_frame.return_value is not None:
                exported_value = stack_frame.return_value
            else:
                # TODO: Maybe wrap in a module type?
                # TODO: Only export attributes called with export
                # TODO: Use identity instead of hashing dict
                exported_value = Dict.from_dict(stack_frame.locals.dict())

        cls._caller_locals()[args[0]] = exported_value

        use.__cache[unique_id] = exported_value

        return exported_value

    @classmethod
    def _set_alias_binding_in_caller_context(
        cls, name: "String", exported_value: Object
    ):
        """Set the alias binding in the caller's lexical scope."""
        # TODO: Handle multiple args potentially
        set_(Args.from_dict({name: exported_value}))


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

    @Special._m_repr_
    def _m_repr_(self):
        from .complex import String

        return String("{" + type(self).__name__ + " " + str(super()._m_repr_()) + "}")


class ExecutionBlock(StatementList, IncompleteExpression):
    def evaluate(self) -> Object:
        caller_stack_frame = current_stack_frame.get()
        with nested_stack_frame() as stack_frame:
            stack_frame.set_parent_lexical_scope(
                caller_stack_frame.lexical_scope
            )
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
        instance.obj = obj
        return instance

    @classmethod
    @Special._m_classcall_
    def _m_classcall_(cls, args: Args, /):
        self = super().__new__(ref)
        key = args[0]
        self.__init__(key)
        return self

    def __str__(self):
        return str(self.obj)

    def __repr__(self):
        return repr(self.obj)

    @Special._m_repr_
    def _m_repr_(self):
        return self.obj._m_repr_()

    # TODO: Implement more


@expose
@function_defined_as_class
@final
class op(Object, FunctionAsClass):
    """Invoke an operation by given operator in Polish notation."""
    from ._operators import operators

    # TODO: Make the operation functions first class citizens
    operators = operators

    def __init__(self, *args):
        super().__init__(*args)

    @classmethod
    @Special._m_classcall_
    def _m_classcall_(cls, args: Args, /):
        # TODO: Validate args
        return op.operators[str(args[0])](*args[1:])

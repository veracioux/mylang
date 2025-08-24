import contextlib
from typing import TYPE_CHECKING, Generic, TypeVar, final

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
    python_dict_from_args_kwargs,
    set_contextvar,
    FunctionAsClass,
)
from .base import Args, Array, Dict, IncompleteExpression, Object

__all__ = ("fun", "call", "get", "set_")


if TYPE_CHECKING:
    from .complex import String

TypeReturn = TypeVar("TypeReturn", bound=Object)


@expose
@function_defined_as_class
class fun(Object, FunctionAsClass, Generic[TypeReturn]):
    _SHOULD_RECEIVE_NEW_STACK_FRAME = False

    def __init__(self, name: Object, /, *args, **kwargs):
        self.name: Object
        self.parameters: Dict
        self.body: StatementList
        self._surrounding_lexical_scope: LexicalScope
        """The lexical scope in which this function was defined."""
        super().__init__(name, *args, **kwargs)

    @classmethod
    @Special._m_classcall_
    def _m_classcall_(cls, args: "Args", /):
        # TODO: Args must have unique names
        func = super().__new__(cls)
        last_positional_index = args.get_last_positional_index()
        if last_positional_index is not None and last_positional_index >= 1:
            func.body = args[last_positional_index]
            assert isinstance(func.body, StatementList), "Body must be a StatementList"
            if last_positional_index >= 1:
                func.name = args[0]
            func.parameters = Args.from_dict(
                dict(enumerate(args[1:-1])) | args.keyed_dict()
            )
            caller_stack_frame = cls._caller_stack_frame()
            caller_stack_frame.locals[func.name] = func
            func._surrounding_lexical_scope = caller_stack_frame.lexical_scope
            return func
        else:
            assert False, (
                "Function requires at least two positional arguments - name and body"
            )

    def __call__(self, *args, **kwargs) -> TypeReturn:
        return call(ref.of(self), *args, **kwargs)

    @Special._m_call_
    def _m_call_(self, _: Args, /) -> TypeReturn:
        return self.body.execute()


@expose
@function_defined_as_class(monkeypatch_methods=False)
class call(Object, FunctionAsClass):
    _SHOULD_RECEIVE_NEW_STACK_FRAME = False

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
        caller_stack_frame = current_stack_frame.get()

        obj_to_call: Object
        if isinstance(_ref := func_key, ref):
            obj_to_call = _ref.obj
        else:
            obj_to_call = caller_stack_frame[func_key]

        needs_new_stack_frame = True

        if isinstance(obj_to_call, type) and issubclass(obj_to_call, FunctionAsClass):
            # Function defined as class
            python_callable = obj_to_call._m_classcall_
            needs_new_stack_frame = obj_to_call._SHOULD_RECEIVE_NEW_STACK_FRAME
        else:
            # Regular MyLang callable
            python_callable = obj_to_call._m_call_

        # Locals of the called function
        _locals = cls._create_locals_for_callable(
            obj_to_call,
            Args(*rest),
        )

        with (
            set_contextvar(currently_called_func, python_callable),
            (
                nested_stack_frame(_locals)
                if needs_new_stack_frame
                else contextlib.nullcontext()
            ) as stack_frame,
        ):
            stack_frame = stack_frame or caller_stack_frame
            if isinstance(func := obj_to_call, fun):  # TODO: Generalize
                stack_frame.set_parent_lexical_scope(func._surrounding_lexical_scope)
            fun_args = Args.from_positional_keyed(rest, args.keyed_dict())
            value = python_callable(fun_args)
            if obj_to_call is not cls:
                caller_stack_frame.lexical_scope.last_called_function = obj_to_call
            return value


    @classmethod
    def _create_locals_for_callable(
        cls,
        callable: Object,
        args: Args,
    ):
        """Create a locals dictionary for `callable` that maps the arguments `args` to the callable's parameters."""
        # TODO: If it is a function implemented in Python, it won't need the bindings to be available in the context,
        #       as it will be able to access the `args` object directly
        locals_ = LocalsDict()

        # TODO: De-hardcode this
        if hasattr(callable, "parameters"):
            for i, posarg in enumerate(callable.parameters[:]):
                locals_[posarg] = args[i]
            keyed_parameters = callable.parameters.keyed_dict()
            keyed_args = args.keyed_dict()
            for key, default_value in keyed_parameters.items():
                locals_[key] = keyed_args.get(key, default_value)

        return locals_


@expose
@function_defined_as_class
class get(Object, FunctionAsClass):
    _SHOULD_RECEIVE_NEW_STACK_FRAME = False

    @classmethod
    @Special._m_classcall_
    def _m_classcall_(cls, args: Args, /):
        # TODO: Proper exception type
        assert len(args) == 1, "get function requires exactly one argument"
        if isinstance(args[0], ref):
            return args[0].obj
        return cls._caller_stack_frame().lexical_scope[args[0]]


@expose
@function_defined_as_class
class set_(Object, FunctionAsClass):
    _SHOULD_RECEIVE_NEW_STACK_FRAME = False
    _m_name_ = Special._m_name_("set")

    @classmethod
    @Special._m_classcall_
    def _m_classcall_(cls, args: Args, /):
        from .primitive import undefined

        lexical_scope_locals = cls._caller_stack_frame().lexical_scope.locals
        for key, value in args._m_dict_.items():
            lexical_scope_locals[key] = value
        return undefined


@expose
@function_defined_as_class
class use(Object, FunctionAsClass):
    """Use code from another file."""
    _SHOULD_RECEIVE_NEW_STACK_FRAME = False

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

            cls._caller_stack_frame().locals[args[0]] = exported_value
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

        cls._caller_stack_frame().locals[args[0]] = exported_value

        use.__cache[unique_id] = exported_value

        return exported_value

    @classmethod
    def _set_alias_binding_in_caller_context(
        cls, name: "String", exported_value: Object
    ):
        """Set the alias binding in the caller's lexical scope."""
        # TODO: Handle multiple args potentially
        set_(Args.from_dict({name: exported_value}))


class StatementList(Array):
    def execute(self) -> Object:
        from . import Args, Object, call, set_, undefined

        for i_statement, statement in enumerate(self):
            result: Object
            # Make sure an expression is converted to Args. If already Args, it
            # won't be modified
            args = Args(statement)

            IncompleteExpression.evaluate_all_in_object(args)

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
    _SHOULD_RECEIVE_NEW_STACK_FRAME = False

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

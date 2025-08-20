from types import MethodType
from typing import TYPE_CHECKING, Generic, TypeVar, final

from . import Object
from .base import Args, Array, Dict, Object
from ._utils import (
    expose,
    function_defined_as_class,
    python_dict_from_args_kwargs,
    python_obj_to_mylang,
    currently_called_func,
    set_contextvar,
)
from ._context import current_context, nested_context, parent_context

__all__ = ("fun", "call", "get", "set", "return_")


if TYPE_CHECKING:
    from .complex import String

TypeReturn = TypeVar("TypeReturn", bound=Object)


@expose
@function_defined_as_class
class fun(Object, Generic[TypeReturn]):
    def __init__(self, name: Object, /, *args, **kwargs):
        self.name: Object
        self.parameters: Dict
        self.body: StatementList
        super().__init__(name, *args, **kwargs)

    def _m_classcall_(cls, args: "Args", /):
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
            current_context.get().parent[func.name] = func
            return func
        else:
            assert False, "Function requires at least two positional arguments - name and body"

    def __call__(self, *args, **kwargs) -> TypeReturn:
        return call(ref.of(self), *args, **kwargs)

    def _m_call_(self, args: Args, /) -> TypeReturn:
        # TODO: check args against parameters
        context = current_context.get()
        for i, posarg in enumerate(self.parameters[:]):
            context[posarg] = args[i]
        # Populate function parameters in the current context
        for key, default_value in self.parameters.keyed_dict():
            context[key] = args.keyed_dict().get(key, default_value)

        return self.body.execute()


@expose
@function_defined_as_class(monkeypatch_methods=False)
class call(Object):
    def __new__(cls, func_key, *args, **kwargs):
        if isinstance(func_key, Args):
            if len(args) > 0 or len(kwargs) > 0:
                raise ValueError(
                    "If the first argument is of type Args, no other arguments are allowed."
                )
            return cls._m_classcall_(None, func_key)
        elif len(args) > 0 and isinstance(mylang_args := args[0], Args):
            if len(args) > 1:
                raise ValueError(
                    "If an argument of type Args is used, it must be the only argument."
                )
            return cls._m_classcall_(None, [func_key] + mylang_args)
        else:
            return cls._m_classcall_(
                None,
                Args.from_dict(python_dict_from_args_kwargs(func_key, *args, **kwargs))
            )

    def __init__(self, func_key, *args, **kwargs):
        super().__init__(func_key, *args, **kwargs)

    def _m_classcall_(cls, args: Args, /):
        func_key, rest = args[0], args[1:]
        with nested_context(args._m_dict_) as new_context:
            obj_to_call: Object
            if isinstance(_ref := func_key, ref):
                obj_to_call = _ref.obj
            else:
                obj_to_call = new_context[func_key]

            if isinstance(obj_to_call, type):
                # Function defined as class
                python_callable = obj_to_call._m_classcall_
            else:
                # Regular MyLang callable
                python_callable = obj_to_call._m_call_.__func__

            with set_contextvar(currently_called_func, python_callable):
                fun_args = Args.from_dict(dict(enumerate(rest)) | args.keyed_dict())
                return python_callable(obj_to_call, fun_args)


@expose
@function_defined_as_class
class get(Object):
    def _m_classcall_(cls, args: Args, /):
        # TODO: Proper exception type
        assert len(args) == 1, "get function requires exactly one argument"
        if isinstance(args[0], ref):
            return args[0].obj
        context = current_context.get()
        return context[args[0]]


@expose
@function_defined_as_class
class set(Object):
    def _m_classcall_(cls, args: Args, /):
        from .primitive import undefined
        context = current_context.get()
        for key, value in args._m_dict_.items():
            context.parent[key] = value
        return undefined


@expose
@function_defined_as_class
class return_(Object):
    _m_name_ = "return"

    def _m_classcall_(cls, args: Args, /):
        # TODO: Make sure return skips execution of remaining statements
        if len(args) != 1:
            raise ValueError("return requires exactly one argument")
        context = current_context.get().parent
        context.return_value = args[0]
        return context.get_return_value()


@expose
@function_defined_as_class
class use(Object):
    """Use code from another file."""
    __cache: dict[str, Object] = {}

    def __init__(self, source: str, /, *, use_cache=True):
        super().__init__(source, use_cache=use_cache)

    def _m_classcall_(cls, args: Args, /):
        from .complex import String

        # TODO: Generalize validation based on __init__ function signature

        if len(args[:]) != 1:
            raise ValueError("use requires exactly one positional argument")

        if not isinstance(args[0], String):
            raise TypeError("use requires a String as the first argument")

        use_cache = True
        if 'use_cache' in args:
            use_cache = args['use_cache']
            from .primitive import Bool
            if not isinstance(use_cache, Bool):
                raise TypeError("use_cache must be a Bool")

        # TODO: Use something more advanced
        unique_id = args[0].value

        if use_cache and unique_id in use.__cache:
            # Return cached value if available
            exported_value = use.__cache[args[0].value]
            use._set_alias_binding_in_caller_context(args[0], exported_value)
            return exported_value

        # TODO: Use a lookup strategy
        # TODO: Support Path in addition to String
        from ...parser import parser, STATEMENT_LIST
        from ...transformer import Transformer

        # TODO: File extension
        with open(args[0].value + ".my", "r") as f:
            code = f.read()
        tree = parser.parse(code, start=STATEMENT_LIST)

        # Enter a nested context, execute the module and obtain its exported
        # value The exported value is either a dict of the module's locals or a
        # specific return value if return was called from within.
        exported_value: Object
        with nested_context({}) as context:
            Transformer().transform(tree)

            if context.return_value is not None:
                exported_value = context.return_value
            else:
                # TODO: Maybe wrap in a module type?
                exported_value = Dict.from_dict(context.own_dict())

        use._set_alias_binding_in_caller_context(args[0], exported_value)
        use.__cache[unique_id] = exported_value

        return exported_value

    @classmethod
    def _set_alias_binding_in_caller_context(cls, name: 'String', exported_value: Object):
        """Set the alias binding in the caller's context."""
        # Set the alias binding in the caller's context
        with parent_context():
            # TODO: Handle multiple args potentially
            set(Args.from_dict({name: exported_value}))


class StatementList(Array):
    def execute(self) -> Object:
        from . import Object, Args, set, call
        for i_statement, statement in enumerate(self):
            result: Object
            # Make sure an expression is converted to Args. If already Args, it
            # won't be modified
            args = Args(statement)

            # Iterate through all top-level items (positional args + keys + values)
            # and make sure that if they are an ExecutionBlock, it gets executed.
            for i_posarg, posarg in enumerate(args[:]):
                if isinstance(posarg, ExecutionBlock):
                    args[i_posarg] = posarg.execute()
            for key, value in args.keyed_dict().items():
                if isinstance(key, ExecutionBlock):
                    key = key.execute()

                args[key] = (
                    value.execute()
                    if isinstance(value, ExecutionBlock)
                    else value
                )

            if args.is_keyed_only():
                result = set(args)
            else:
                result = call(args)

            if i_statement == len(self) - 1:
                return result

    def _m_repr_(self):
        from .complex import String
        return String("{" + type(self).__name__ + " " + str(super()._m_repr_()) + "}")


class ExecutionBlock(StatementList):
    def execute(self) -> Object:
        with nested_context({}):
            return super().execute()


@expose
@function_defined_as_class
@final
class ref(Object):
    def __init__(self, key: Object):
        from ._context import current_context

        # TODO: For some reason `ref 1` doesn't throw, even though I didn't
        # explicitly assign set 1=...

        self.obj = current_context.get()[key]

    @classmethod
    def of(cls, obj: Object, /):
        """Create a reference to an object."""
        instance = super().__new__(cls)
        instance.obj = obj
        return instance

    def _m_classcall_(cls, args: Args, /):
        self = super().__new__(ref)
        key = args[0]
        self.__init__(key)
        return self

    def __str__(self):
        return str(self.obj)

    def __repr__(self):
        return repr(self.obj)

    def _m_repr_(self):
        return self.obj._m_repr_()

    # TODO: Implement more

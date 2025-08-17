from typing import Generic, TypeVar

from mylang.stdlib.core.primitive import Int

from .base import Args, Array, Dict, Object, Ref
from ._utils import (
    expose,
    function_defined_as_class,
    python_dict_from_args_kwargs,
    python_obj_to_mylang,
    currently_called_func,
    set_contextvar,
)
from ._context import current_context, nested_context

__all__ = ("fun", "call", "get", "set", "return_")


TypeReturn = TypeVar("TypeReturn", bound=Object)


@expose
class fun(Dict, Generic[TypeReturn]):
    def __init__(self, name: Object, /, *args, **kwargs):
        self.name: Object
        self.parameters: Dict
        self.body: Array[Args]
        super().__init__(name, *args, **kwargs)

    def _m_init_(self, args: "Args", /):
        last_positional_index = args.get_last_positional_index()
        if last_positional_index is not None and last_positional_index >= 1:
            self.body = args[last_positional_index]
            if last_positional_index >= 1:
                self.name = args[0]
            self.parameters = python_obj_to_mylang(
                {k: v for k, v in args._m_dict_.items() if k != last_positional_index}
            )
        else:
            raise ValueError(
                "Function requires at least two positional arguments - name and body"
            )

    def __call__(self, *args, **kwargs) -> TypeReturn:
        return call(Ref.of(self), *args, **kwargs)

    def _m_call_(self, args: Args, /) -> TypeReturn:
        # TODO: check args against parameters
        context = current_context.get()
        # Populate function parameters in the current context
        for key, value in args._m_dict_.items():
            context[key] = value
        for statement in self.body:
            # TODO properly handle
            assert isinstance(statement, Args)
            if Int(0) not in statement._m_dict_:
                # If there are no positional arguments, this is an assignment;
                # call `set`
                # TODO properly handle
                assert len(statement) == 1
                set(statement)
            else:
                # Otherwise, this is a function call;
                # call `call`
                # TODO properly handle
                assert len(statement) > 0
                call(statement)

        return context.return_value


@expose
@function_defined_as_class(monkeypatch_methods=False)
class call(Object):
    def __new__(cls, func_key, *args, **kwargs):
        if isinstance(func_key, Args):
            if len(args) > 0 or len(kwargs) > 0:
                raise ValueError(
                    "If the first argument is of type Args, no other arguments are allowed."
                )
            return cls._m_call_(func_key)
        elif len(args) > 0 and isinstance(mylang_args := args[0], Args):
            if len(args) > 1:
                raise ValueError(
                    "If an argument of type Args is used, it must be the only argument."
                )
            return cls._m_call_([func_key] + mylang_args)
        else:
            return cls._m_call_(
                Args.from_dict(python_dict_from_args_kwargs(func_key, *args, **kwargs))
            )

    def __init__(self, *args, **kwargs):
        pass

    @classmethod
    def _m_call_(cls, args: Args, /):
        func_key, rest = args[0], args[1:]
        with nested_context(args._m_dict_) as new_context:
            obj_to_call: Object
            if isinstance(ref := func_key, Ref):
                obj_to_call = ref.obj
            else:
                obj_to_call = new_context[func_key]

            with set_contextvar(currently_called_func, obj_to_call):
                return python_obj_to_mylang(
                    obj_to_call._m_call_(
                        Args.from_dict(dict(enumerate(rest)) | args.keyed_dict())
                    )
                )


@expose
@function_defined_as_class
class get(Object):
    @classmethod
    def _m_call_(cls, args: Args, /):
        # TODO: Proper exception type
        assert len(args) == 1, "get function requires exactly one argument"
        if isinstance(args[0], Ref):
            return args[0].obj
        context = current_context.get()
        return context[args[0]]


@expose
@function_defined_as_class
class set(Object):
    @classmethod
    def _m_call_(cls, args: Args, /):
        context = current_context.get()
        for key, value in args._m_dict_.items():
            context.parent[key] = value


@expose
@function_defined_as_class
class return_(Object):
    _m_name_ = "return"

    @classmethod
    def _m_call_(cls, args: Args, /):
        if len(args) != 1:
            raise ValueError("return requires exactly one argument")
        context = current_context.get().parent
        context.return_value = args[0]
        return context.return_value

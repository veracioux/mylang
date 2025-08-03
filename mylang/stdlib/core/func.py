from typing import Any, Generic, TypeVar

from .base import Args, Array, Dict, Object, Ref
from ._utils import (
    function_defined_as_class,
    all_functions_defined_as_classes,
    python_dict_from_args_kwargs,
    python_obj_to_mylang,
    currently_called_func,
    set_contextvar,
)
from ._context import current_context, nested_context


TypeReturn = TypeVar("TypeReturn", bound=Object)


class FunMeta(type):
    def __instancecheck__(cls, instance: Any, /) -> bool:
        if super().__instancecheck__(instance):
            return True
        elif instance in all_functions_defined_as_classes:
            return True
        else:
            return False


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
        raise NotImplementedError


@function_defined_as_class(monkeypatch_methods=False)
class call(Object):
    def __new__(cls, func_key, *args, **kwargs):
        if isinstance(func_key, Args):
            if len(args) > 0 or len(kwargs) > 0:
                raise ValueError("If the first argument is of type Args, no other arguments are allowed.")
            return cls._m_call_(func_key)
        elif len(args) > 0 and isinstance(mylang_args := args[0], Args):
            if len(args) > 1:
                raise ValueError("If an argument of type Args is used, it must be the only argument.")
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


@function_defined_as_class
class get(Object):
    @classmethod
    def _m_call_(cls, args: Args, /):
        raise NotImplementedError


@function_defined_as_class
class set(Object):
    @classmethod
    def _m_call_(cls, args: Args, /):
        context = current_context.get()
        for key, value in args._m_dict_.items():
            context.parent[key] = value

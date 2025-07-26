from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from mylang.stdlib.core.base import Object


def python_obj_to_mylang(obj):
    """Convert a Python object to a MyLang object."""
    from .base import Object

    if isinstance(obj, Object):
        return obj
    elif isinstance(obj, str):
        from .complex import String
        return String(obj)
    elif isinstance(obj, dict):
        from .base import Dict
        return Dict.from_dict(obj)
    elif isinstance(obj, int):
        from .primitive import Int
        return Int(obj)
    elif obj is None:
        from .primitive import undefined
        return undefined
    else:
        raise NotImplementedError


def python_dict_from_args_kwargs(*args, **kwargs):
    return {
        **{python_obj_to_mylang(i): python_obj_to_mylang(arg) for i, arg in enumerate(args)},
        **{python_obj_to_mylang(k): python_obj_to_mylang(v) for k, v in kwargs.items()},
    }


def mylang_obj_to_python(obj: 'Object'):
    from .complex import String
    from .base import Dict, Args, Object
    from .primitive import Scalar, Bool, undefined, null

    if isinstance(obj, String):
        return obj.value
    elif isinstance(obj, (Dict, Args)):
        return {mylang_obj_to_python(k): mylang_obj_to_python(v) for k, v in obj._m_dict_.items()}
    elif isinstance(obj, Scalar):
        return obj.value
    elif isinstance(obj, Bool):
        return obj.value
    elif obj in (undefined, null):
        return None
    elif not isinstance(obj, Object):
        if isinstance(obj, dict):
            return {mylang_obj_to_python(k): mylang_obj_to_python(v) for k, v in obj.items()}
        # TODO: Other sequences?
        else:
            return obj
    else:
        raise NotImplementedError


def mylang_dict_from_args_kwargs(*args, **kwargs):
    """Convert args and kwargs to a Dict."""
    return python_obj_to_mylang(python_dict_from_args_kwargs)

from contextlib import contextmanager
from contextvars import ContextVar
import functools
from types import FunctionType
from typing import TYPE_CHECKING, Any, TypeVar


if TYPE_CHECKING:
    from .base import Object
    from .func import fun


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
    elif isinstance(obj, list):
        from .base import Array
        return Array.from_list(obj)
    elif obj is None:
        from .primitive import undefined
        return undefined
    elif obj in all_functions_defined_as_classes:
        return obj
    else:
        raise NotImplementedError


def python_dict_from_args_kwargs(*args, **kwargs):
    return dict(enumerate(args), **kwargs)


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


TypeFunc = TypeVar('TypeFunc', bound=FunctionType)


all_functions_defined_as_classes: set[type] = set()


def function_defined_as_class(cls=None, /, *, monkeypatch_methods=True) -> 'fun':
    def decorator(cls):
        from .complex import String

        # Check the class for disallowed attributes
        if monkeypatch_methods:
            disallowed_attrs = ('__init__', '__call__')
            for attr in disallowed_attrs:
                if attr in vars(cls):
                    raise ValueError(f'class used as a function must not have {attr} method defined')

        # Register the class as a function
        all_functions_defined_as_classes.add(cls)

        # Treating the class as a function,

        # Set the function name
        cls.name = python_obj_to_mylang(cls._m_name_) if hasattr(cls, '_m_name_') else String(cls.__name__)

        if monkeypatch_methods:
            # Make sure that the class can never be called by anything other than `call`
            def _m_call_decorator(_m_call_):
                @functools.wraps(_m_call_)
                def wrapper(*args, **kwargs):
                    assert currently_called_func.get() is cls
                    return _m_call_(*args, **kwargs)
                return wrapper
            cls._m_call_ = _m_call_decorator(cls._m_call_)

            # Use fun.__call__ as cls.__new__
            # NOTE: Cannot just do cls.__call__ = fun.__call__ because it would
            # result in a recursive import
            def fun__call__(self, *args, **kwargs):
                from .func import fun
                return fun.__call__(self, *args, **kwargs)
            cls.__new__ = fun__call__
            cls.__init__ = lambda self, *args, **kwargs: None

        # TODO: initialize parameters and body
        return cls

    if cls is not None:
        return decorator(cls)
    else:
        return decorator


currently_called_func = ContextVar('currently_called_func', default=None)


def expose(obj: 'Object'):
    """Expose the object outside of Python."""
    raise NotImplementedError


@contextmanager
def set_contextvar(contextvar: 'ContextVar', value: Any):
    """Set the current context to the given context."""
    reset_token = contextvar.set(value)
    try:
        yield
    finally:
        contextvar.reset(reset_token)

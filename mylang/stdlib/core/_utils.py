from contextlib import contextmanager
from contextvars import ContextVar
import functools
from types import FunctionType, MethodType, MethodWrapperType
from typing import TYPE_CHECKING, Any, TypeVar
from weakref import WeakKeyDictionary, WeakSet


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
        from .base import Object

        # Register the class as a function
        all_functions_defined_as_classes.add(cls)

        # Set the function name
        cls.name = (
            python_obj_to_mylang(cls._m_name_)
            if hasattr(cls, '_m_name_')
            else String(cls.__name__)
        )

        if monkeypatch_methods:
            if hasattr(cls, '_m_classcall_'):
                cls._m_classcall_ = only_callable_by_call_decorator(cls._m_classcall_)
            if hasattr(cls, '_m_call_'):
                cls._m_call_ = only_callable_by_call_decorator(cls._m_call_)

            # Make sure that cls(...) will call the function via `call`
            def __new__(cls, *args, **kwargs):
                from .func import call
                from . import ref
                if currently_called_func.get() is __new__:
                    with set_contextvar(currently_called_func, cls._m_classcall_):
                        return cls._m_classcall_(*args, **kwargs)
                return call(ref.of(cls), *args, **kwargs)
            cls.__new__ = __new__

        # TODO: initialize parameters and body
        return cls

    if cls is not None:
        return decorator(cls)
    else:
        return decorator


currently_called_func = ContextVar('currently_called_func', default=None)
"""Used by `only_callable_by_call_decorator` to ensure that a function can only
be called from `call`."""

_exposed_objects = set[int]()
"""Holds all objects that are exposed outside of Python, in the context of MyLang."""


TypeObject = TypeVar('TypeObject', bound='Object')


def expose(obj: TypeObject):
    """Expose the object outside of Python."""
    _exposed_objects.add(id(obj))
    # TODO: Make sure that callables are decorated by only_callable_by_call_decorator
    # (need to determine how to recognize something as a callable)
    return obj


def is_exposed(obj: 'Object'):
    """Check if the object is exposed outside of Python."""
    return id(obj) in _exposed_objects


@contextmanager
def set_contextvar(contextvar: 'ContextVar', value: Any):
    """Set the current context to the given context."""
    reset_token = contextvar.set(value)
    try:
        yield
    finally:
        contextvar.reset(reset_token)


def only_callable_by_call_decorator(func):
    """Decorator to ensure that a function can only be called from `call`.

    Call sets `currently_called_func` to the function being called, and this
    verifies that that is the case.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        assert currently_called_func.get() is wrapper, f"MyLang-exposed callable can only be called from `call`"
        return func(*args, **kwargs)
    return wrapper

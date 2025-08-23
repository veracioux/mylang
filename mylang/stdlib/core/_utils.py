import abc
from contextlib import contextmanager
from contextvars import ContextVar
import functools
from types import FunctionType, MethodType
from typing import TYPE_CHECKING, Any, TypeVar


if TYPE_CHECKING:
    from .base import Object, Args
    from .func import fun


T = TypeVar("T")


class _SpecialAttrDescriptor:
    def __set_name__(self, owner: "Special", name: str):
        self.name = name

    def __get__(self, instance, owner) -> "_SpecialAttrDescriptor":
        if instance is not None:
            raise RuntimeError(f"Cannot use {self.__class__.__name__} with instance")

        return self

    def __call__(self, value: T) -> T:
        if callable(value) and value.__name__ != self.name:
            raise ValueError(f"Function name must match special attribute name {self.name}. Got {value.__name__}")

        return value

    def __set__(self, instance, value):
        raise AttributeError(f"Cannot set attribute {self.name}")


class Special:
    """A registry of all special attributes that MyLang uses, for better
    maintainability, discoverability and easier refactoring.

    Example:
        class MyClass:
            _m_dict_ = Special._m_dict_(value)
    """
    _m_dict_ = _SpecialAttrDescriptor()
    _m_array_ = _SpecialAttrDescriptor()
    _m_name_ = _SpecialAttrDescriptor()
    _m_init_ = _SpecialAttrDescriptor()
    _m_str_ = _SpecialAttrDescriptor()
    _m_repr_ = _SpecialAttrDescriptor()
    _m_setattr_ = _SpecialAttrDescriptor()
    _m_call_ = _SpecialAttrDescriptor()
    _m_classcall_ = _SpecialAttrDescriptor()


def python_obj_to_mylang(obj):
    """Convert a Python object to a MyLang analog."""
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
    elif isinstance(obj, FunctionType):
        return _python_func_to_mylang(obj)
    elif obj in all_functions_defined_as_classes:
        return obj
    else:
        raise NotImplementedError


def python_dict_from_args_kwargs(*args, **kwargs):
    return dict(enumerate(args), **kwargs)


def mylang_obj_to_python(obj: "Object"):
    from .complex import String
    from .base import Dict, Args, Object
    from .primitive import Scalar, Bool, undefined, null

    if isinstance(obj, String):
        return obj.value
    elif isinstance(obj, (Dict, Args)):
        return {
            mylang_obj_to_python(k): mylang_obj_to_python(v)
            for k, v in obj._m_dict_.items()
        }
    elif isinstance(obj, Scalar):
        return obj.value
    elif isinstance(obj, Bool):
        return obj.value
    elif obj in (undefined, null):
        return None
    elif not isinstance(obj, Object):
        if isinstance(obj, dict):
            return {
                mylang_obj_to_python(k): mylang_obj_to_python(v) for k, v in obj.items()
            }
        # TODO: Other sequences?
        else:
            return obj
    else:
        raise NotImplementedError


TypeFunc = TypeVar("TypeFunc", bound=FunctionType)


all_functions_defined_as_classes: set[type] = set()


class FunctionAsClass(abc.ABC):
    _SHOULD_RECEIVE_NEW_STACK_FRAME = True
    """Indicates that the function should receive a nested stack frame.

    Cautiously override this attribute. It is intended for control flow
    functions that need direct access to the caller's stack frame.
    """

    @classmethod
    @abc.abstractmethod
    @Special._m_classcall_
    def _m_classcall_(cls, args: "Args", /) -> "Object":
        """Called by the `call` function.

        The `call` function is responsible for providing a fresh `StackFrame` to this function.

        DO NOT CALL THIS DIRECTLY.
        """

    @classmethod
    def _caller_stack_frame(cls):
        if cls._SHOULD_RECEIVE_NEW_STACK_FRAME:
            raise RuntimeError(
                " ".join(
                    f"""
                        If function {cls.__name__} wants access to the caller's stack frame,
                        it should set its class attribute _SHOULD_RECEIVE_NEW_STACK_FRAME to False
                    """.split()
                )
            )
        from ._context import current_stack_frame

        return current_stack_frame.get()


def function_defined_as_class(cls=None, /, *, monkeypatch_methods=True) -> "fun":
    def decorator(cls: FunctionAsClass):
        assert isinstance(cls, type) and issubclass(cls, FunctionAsClass), (
            f"Class {cls.__name__} should be a subclass of FunctionAsClass"
        )

        from .complex import String

        # Register the class as a function
        all_functions_defined_as_classes.add(cls)

        # Set the function name
        cls.name = (
            python_obj_to_mylang(cls._m_name_)
            if hasattr(cls, Special._m_name_.name)
            else String(cls.__name__)
        )

        if monkeypatch_methods:
            cls._m_classcall_ = Special._m_classcall_(only_callable_by_call_decorator(cls._m_classcall_))
            if hasattr(cls, Special._m_call_.name):
                cls._m_call_ = Special._m_call_(only_callable_by_call_decorator(cls._m_call_))

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


currently_called_func = ContextVar("currently_called_func", default=None)
"""Used by `only_callable_by_call_decorator` to ensure that a function can only
be called from `call`."""

_exposed_objects = set[int]()
"""Holds all objects that are exposed outside of Python, in the context of MyLang."""


TypeObject = TypeVar("TypeObject", bound="Object")


def expose(obj: TypeObject):
    """Expose the object outside of Python."""
    _exposed_objects.add(id(obj))
    # TODO: Make sure that callables are decorated by only_callable_by_call_decorator
    # (need to determine how to recognize something as a callable)
    return obj


def is_exposed(obj: "Object"):
    """Check if the object is exposed outside of Python."""
    return id(obj) in _exposed_objects


@contextmanager
def set_contextvar(contextvar: "ContextVar", value: Any):
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
        called_func = currently_called_func.get()
        assert called_func is wrapper or (
            isinstance(called_func, MethodType) and called_func.__func__ is wrapper
        ), f"MyLang-exposed callable can only be called from `call`"
        return func(*args, **kwargs)

    return wrapper


def _python_func_to_mylang(func: FunctionType) -> "Object":
    """Convert a Python function to a MyLang function."""
    from .base import Object, Args
    from .func import FunctionAsClass

    @function_defined_as_class
    class __func(Object, FunctionAsClass):
        @classmethod
        @Special._m_classcall_
        def _m_classcall_(cls, args: "Args", /):
            """Call the function with the given arguments."""
            return func(*args[:], **args.keyed_dict())

    __func.__name__ = func.__name__

    return __func

import abc
from contextlib import contextmanager
from contextvars import ContextVar
import functools
from types import FunctionType, MethodType
from typing import TYPE_CHECKING, Any, TypeVar, Generic, Union

if TYPE_CHECKING:
    from .base import Object, Args
    from ._context import LocalsDict
    from .class_ import class_


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
    """Called when the instance is called by the `call` function.
    The `call` function takes care of setting up the local context before it makes this call.
    Parameters
        args : `Args`
            The arguments this function was called with. The implementation of `_m_call_` may use these
            arguments directly, or it can obtain them from the local context, where those arguments are mapped
            to local keys based on the args and the callable (self)'s parameter signature.
    """
    _m_classcall_ = _SpecialAttrDescriptor()
    _m_lexical_scope_ = _SpecialAttrDescriptor()


def python_obj_to_mylang(obj):
    """Convert a Python object to a MyLang analog."""
    from .base import Object

    if isinstance(obj, Object):
        return obj
    elif isinstance(obj, type) and issubclass(obj, Object):
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

        return Array.from_iterable(obj)
    elif obj is None:
        from .primitive import undefined

        return undefined
    elif isinstance(obj, FunctionType):
        return _python_func_to_mylang(obj)
    elif isinstance(obj, MethodType):
        return _python_func_to_mylang(obj)
    elif obj in all_functions_defined_as_classes:
        return obj
    else:
        raise NotImplementedError(f"{python_obj_to_mylang.__name__} is not implemented for type {type(obj)}")


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
        return obj


TypeFunc = TypeVar("TypeFunc", bound=FunctionType)


all_functions_defined_as_classes: set[type] = set()


TypeReturn = TypeVar("TypeReturn", bound="Object")


class FunctionAsClass(abc.ABC, Generic[TypeReturn]):
    _CLASSCALL_SHOULD_RECEIVE_NEW_STACK_FRAME = True
    """Indicates that `_m_classcall_` should receive a nested stack frame.

    Cautiously override this attribute. It is intended for control flow
    functions that need direct access to the caller's stack frame.
    """
    _CALL_SHOULD_RECEIVE_NEW_STACK_FRAME = True
    """Indicates that `_m_call_` should receive a nested stack frame.

    Cautiously override this attribute. It is intended for control flow
    functions that need direct access to the caller's stack frame.
    """

    def __call__(self, *args, **kwargs) -> TypeReturn:
        from .func import call, ref
        return call(ref.of(self), *args, **kwargs)

    @classmethod
    @abc.abstractmethod
    @Special._m_classcall_
    def _m_classcall_(cls, args: "Args", /) -> "Object":
        """Called by the `call` function.

        The `call` function is responsible for providing a fresh `StackFrame`
        to this function.

        DO NOT CALL THIS DIRECTLY.
        """

    @classmethod
    def _caller_stack_frame(cls):
        """Get the stack frame of the caller of this function.

        If _CLASSCALL_SHOULD_RECEIVE_NEW_STACK_FRAME is True, this will be the
        parent of the current stack frame. If False, it will be the current
        stack frame.
        """
        from ._context import current_stack_frame

        this_stack_frame = current_stack_frame.get()
        return (
            this_stack_frame.parent
            if cls.__should_receive_new_stack_frame()
            else this_stack_frame
        )

    @classmethod
    def _caller_lexical_scope(cls):
        """Get the lexical scope of the caller of this function.

        Similar to `_caller_stack_frame`, if
        `_CLASSCALL_SHOULD_RECEIVE_NEW_STACK_FRAME` is True, this will be the
        lexical scope of the current stack frame's parent. If False, it will be
        the lexical scope of the current stack frame.
        """
        return cls._caller_stack_frame().lexical_scope

    @classmethod
    def _caller_locals(cls):
        """Get the locals of the caller of this function.

        Similar to `_caller_stack_frame`, if
        `_CLASSCALL_SHOULD_RECEIVE_NEW_STACK_FRAME` is True, this will be the
        lexical scope of the current stack frame's parent. If False, it will be
        the lexical scope of the current stack frame.
        """
        return cls._caller_stack_frame().locals

    @classmethod
    def __should_receive_new_stack_frame(cls):
        from .func import call
        current_func = currently_called_func.get()
        if cls is call:  # `call` is a special case: it doesn't get currently_called_func set
            return cls._CLASSCALL_SHOULD_RECEIVE_NEW_STACK_FRAME
        if current_func.__name__ == Special._m_classcall_.name:
            return cls._CLASSCALL_SHOULD_RECEIVE_NEW_STACK_FRAME
        elif current_func.__name__ == Special._m_call_.name:
            return cls._CALL_SHOULD_RECEIVE_NEW_STACK_FRAME
        else:
            raise NotImplementedError


def function_defined_as_class(cls=None, /, *, monkeypatch_methods=True):
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
            cls._m_classcall_ = classmethod(
                only_callable_by_call_decorator(cls._m_classcall_.__func__),
            )
            if hasattr(cls, Special._m_call_.name):
                cls._m_call_ = Special._m_call_(only_callable_by_call_decorator(cls._m_call_))

            # Make sure that cls(...) will call the function via `call`
            def __new__(cls, *args, **kwargs):
                from .func import call, ref

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


_exposed_class_attrs = set[tuple[type, str]]()
"""Holds all (class, attr_name) pairs that are exposed to MyLang."""


_exposed_obj_attrs = set[tuple[type, str]]()
"""Holds (class, attr_name) pairs. Each pair means that the attribute named
`attr_name` should be exposed to MyLang for instances of `class` and its subclasses."""


TypeObject = TypeVar("TypeObject", bound="Object")


def expose(obj: TypeObject):
    """Expose the object outside of Python."""
    _exposed_objects.add(id(obj))
    # TODO: Make sure that callables are decorated by only_callable_by_call_decorator
    # (need to determine how to recognize something as a callable)
    return obj


def expose_class_attr(attr_name: str):
    """Decorator to expose a class attribute in the context of MyLang."""
    def decorator(cls):
        _exposed_class_attrs.add((cls, attr_name))
        return cls

    return decorator


def is_exposed(obj: "Object"):
    """Check if the object is exposed outside of Python."""
    return id(obj) in _exposed_objects


def is_attr_exposed(obj: "Object", attr_name: str):
    """Check if the given attribute on obj is exposed outside of Python."""
    if (obj, attr_name) in _exposed_obj_attrs:
        return True

    type_ = obj if isinstance(obj, type) else type(obj)

    for type_ in type_.mro()[:-1]:  # exclude `object`
        if (type_, attr_name) in _exposed_class_attrs:
            return True

    return False


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
    from .func import StatementList

    @function_defined_as_class
    class __func(Object, FunctionAsClass):
        if func.__name__ != "<lambda>":
            _m_name_ = Special._m_name_(func.__name__)

        @classmethod
        @Special._m_classcall_
        def _m_classcall_(cls, args: "Args", /):
            """Call the function with the given arguments."""
            return func(*args[:], **args.keyed_dict())

    # TODO: Set correct values
    __func.parameters = Args()
    __func.body = StatementList()

    __func.__name__ = func.__name__
    __func.__qualname__ = func.__qualname__

    return __func


def populate_locals_for_callable(
    locals_: "LocalsDict",
    parameters: "Args",
    args: "Args",
):
    """Populate a locals dictionary for a callable by mapping the arguments `args` to the callable's `parameters`."""
    for i, posarg in enumerate(parameters[:]):
        locals_[posarg] = args[i]
    keyed_parameters = parameters.keyed_dict()
    keyed_args = args.keyed_dict()
    for key, default_value in keyed_parameters.items():
        locals_[key] = keyed_args.get(key, default_value)

    return locals_


# TODO: Implement python-like getattr attribute lookup
def getattr_(obj: "Object", key: "Object"):
    from ._context import LexicalScope, LocalsDict
    from .base import TypedObject, Dict, Object
    from .complex import String

    if isinstance(obj, (Dict, LexicalScope, LocalsDict)):
        return obj[key]
    elif isinstance(obj, Object) or (isinstance(obj, type) and issubclass(obj, FunctionAsClass)):
        # Try to access via _m_dict_ first
        try:
            m_dict = getattr(obj, Special._m_dict_.name)
            return m_dict[key]
        except:
            # Try to access on class prototype if applicable
            if isinstance(obj, TypedObject):
                from .class_ import Method
                try:
                    value = obj.type_.prototype[key]
                    if isinstance(value, Method):
                        return value.bind(obj)
                    else:
                        return value
                except:
                    pass
            # Try to access directly on Python object
            if isinstance(key, String) and is_attr_exposed(obj, key.value):
                try:
                    return getattr(obj, key.value)
                except:
                    pass
            assert False, f"Object {obj} has no attribute {key}"
    raise NotImplementedError(f"_getattr not implemented for type {type(obj)}")


def isinstance_(obj: "Object", type_: type):
    """Instance check in the context of MyLang."""
    from .base import TypedObject
    from .func import fun
    if isinstance(obj, TypedObject):
        return issubclass_(obj.type_, type_)
    elif isinstance(obj, type_):
        return True
    elif isinstance(obj, type) and issubclass(obj, FunctionAsClass) and type_ is fun:
        return True
    else:
        return False


def issubclass_(obj: "Object", type_: Union[type, "class_"]):
    """Subclass check in the context of MyLang."""
    from .class_ import class_
    from .base import Object

    if type_ is Object:
        return True

    if isinstance(obj, type) and isinstance(type_, type) and issubclass(obj, type_):
        return True
    elif isinstance(obj, class_):
        if obj is type_:
            return True
        if obj.bases == (Object,):
            return False
        return any(issubclass_(base, type_) for base in obj.bases)
    else:
        return False

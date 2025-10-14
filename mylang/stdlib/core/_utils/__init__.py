import abc
import functools
from contextlib import contextmanager
from contextvars import ContextVar
from types import FunctionType, MethodType, ModuleType
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    Optional,
    TypeVar,
    Union,
)


from .exposure import (
    expose,
    expose_obj_attr,
    expose_instance_attr,
    expose_class_attr,
    is_exposed,
    is_attr_exposed,
    export_object_from_module,
    get_actual_python_module_export,
)


from .context import require_parent_stack_frame, require_parent_lexical_scope, require_parent_locals


# Re-export
__all__ = (
    "expose",
    "expose_obj_attr",
    "expose_instance_attr",
    "expose_class_attr",
    "is_exposed",
    "is_attr_exposed",
    "iter_",
    "repr_",
    "str_",
    "python_obj_to_mylang",
    "python_dict_from_args_kwargs",
    "mylang_obj_to_python",
    "function_defined_as_class",
    "getattr_",
    "isinstance_",
    "issubclass_",
    "getname",
    "require_parent_stack_frame",
    "require_parent_lexical_scope",
    "require_parent_locals",
    "export_object_from_module",
    "get_actual_python_module_export",
)


if TYPE_CHECKING:
    from .._context import LocalsDict
    from ..base import Args, Object
    from ..complex import String
    from ..class_ import class_


T = TypeVar("T")


def python_obj_to_mylang(obj) -> "Object":
    """Convert a Python object to a MyLang analog."""
    from ..base import Object

    if isinstance(obj, Object):
        return obj
    elif isinstance(obj, type) and issubclass(obj, Object):
        return obj
    elif isinstance(obj, str):
        from ..complex import String

        return String(obj)
    elif isinstance(obj, dict):
        from ..base import Dict

        return Dict.from_dict(obj)
    elif isinstance(obj, int):
        from ..primitive import Int

        return Int(obj)
    elif isinstance(obj, list):
        from ..base import Array

        return Array.from_iterable(obj)
    elif isinstance(obj, ModuleType):
        from .types import PythonModuleWrapper

        return PythonModuleWrapper(obj)
    elif obj is None:
        from ..primitive import undefined

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
    from ..base import Args, Dict, Object
    from ..complex import String
    from ..primitive import Bool, Scalar, null, undefined

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
        return obj


TypeFunc = TypeVar("TypeFunc", bound=FunctionType)


all_functions_defined_as_classes: set["FunctionAsClass"] = set()


TypeReturn = TypeVar("TypeReturn", bound="Object")


class FunctionAsClass(abc.ABC, Generic[TypeReturn]):
    _CLASSCALL_SHOULD_RECEIVE_NEW_STACK_FRAME: Optional[bool] = None
    """Indicates that `_m_classcall_` should receive a nested stack frame.

    Cautiously override this attribute. It is intended for control flow
    functions that need direct access to the caller's stack frame.
    """
    _CALL_SHOULD_RECEIVE_NEW_STACK_FRAME: Optional[bool] = None
    """Indicates that `_m_call_` should receive a nested stack frame.

    Cautiously override this attribute. It is intended for control flow
    functions that need direct access to the caller's stack frame.
    """

    def __call__(self, *args, **kwargs) -> TypeReturn:
        from ..func import call, ref

        return call(ref.of(self), *args, **kwargs)

    @classmethod
    @abc.abstractmethod
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
        from .._context import current_stack_frame

        this_stack_frame = current_stack_frame.get()
        stack_frame = this_stack_frame.parent if cls.__should_receive_new_stack_frame() else this_stack_frame
        assert stack_frame is not None, "_caller_stack_frame: No caller stack frame found"
        return stack_frame

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
        from ..func import call

        current_func = currently_called_func.get()
        if cls is call:  # `call` is a special case: it doesn't get currently_called_func set
            return cls._CLASSCALL_SHOULD_RECEIVE_NEW_STACK_FRAME
        if current_func.__name__ == "_m_classcall_":
            return cls._CLASSCALL_SHOULD_RECEIVE_NEW_STACK_FRAME
        elif current_func.__name__ == "_m_call_":
            return cls._CALL_SHOULD_RECEIVE_NEW_STACK_FRAME
        else:
            raise NotImplementedError


def function_defined_as_class(cls=None, /, *, monkeypatch_methods=True):
    def decorator(cls: FunctionAsClass):
        assert isinstance(cls, type) and issubclass(
            cls, FunctionAsClass
        ), f"Class {cls.__name__} should be a subclass of FunctionAsClass"
        assert (
            not hasattr(cls, "_m_classcall_") or cls._CLASSCALL_SHOULD_RECEIVE_NEW_STACK_FRAME is not None
        ), "Please explicitly set _CLASSCALL_SHOULD_RECEIVE_NEW_STACK_FRAME to desired bool"
        assert (
            not hasattr(cls, "_m_call_") or cls._CALL_SHOULD_RECEIVE_NEW_STACK_FRAME is not None
        ), "Please explicitly set _CALL_SHOULD_RECEIVE_NEW_STACK_FRAME to desired bool"

        from ..complex import String

        # Register the class as a function
        all_functions_defined_as_classes.add(cls)

        # Set the function name
        cls.name = python_obj_to_mylang(cls._m_name_) if hasattr(cls, "_m_name_") else String(cls.__name__)

        if monkeypatch_methods:
            cls._m_classcall_ = classmethod(
                only_callable_by_call_decorator(cls._m_classcall_.__func__),
            )
            if hasattr(cls, "_m_call_"):
                cls._m_call_ = only_callable_by_call_decorator(cls._m_call_)

            # Make sure that cls(...) will call the function via `call`
            def __new__(cls, *args, **kwargs):
                from ..func import call, ref

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
        ), "MyLang-exposed callable can only be called from `call`"
        return func(*args, **kwargs)

    return wrapper


def _python_func_to_mylang(func: FunctionType) -> "Object":
    """Convert a Python function to a MyLang function."""
    from ..base import Args, Object
    from ..func import StatementList

    @function_defined_as_class
    class __func(Object, FunctionAsClass):
        _CLASSCALL_SHOULD_RECEIVE_NEW_STACK_FRAME = True
        if func.__name__ != "<lambda>":
            _m_name_ = func.__name__

        @classmethod
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
    from .._context import LexicalScope, LocalsDict
    from ..base import Dict, Object, TypedObject
    from ..complex import String
    from .types import PythonModuleWrapper

    if hasattr(obj, "_m_getattr_"):
        return obj._m_getattr_(key)
    elif isinstance(obj, (Dict, LexicalScope, LocalsDict)):
        return obj[key]
    elif isinstance(obj, PythonModuleWrapper):
        if isinstance(key, String) and is_attr_exposed(obj.module, key.value):
            return getattr(obj.module, key.value)
        else:
            assert False, f"Object {obj} has no attribute {key}"
    elif isinstance(obj, Object) or (isinstance(obj, type) and issubclass(obj, FunctionAsClass)):
        # Try to access via _m_dict_ first
        try:
            m_dict = obj._m_dict_
            return m_dict[key]
        except Exception:
            # Try to access on class prototype if applicable
            if isinstance(obj, TypedObject):
                from ..class_ import Method

                try:
                    value = obj.type_.prototype[key]
                    if isinstance(value, Method):
                        return value.bind(obj)
                    else:
                        return value
                except Exception:
                    pass
            # Try to access directly on Python object
            if isinstance(key, String) and is_attr_exposed(obj, key.value):
                try:
                    return getattr(obj, key.value)
                except Exception:
                    pass
            assert False, f"Object {obj} has no attribute {key}"
    raise NotImplementedError(f"_getattr not implemented for type {type(obj)}")


def isinstance_(obj: "Object", type_: type):
    """Instance check in the context of MyLang."""
    from ..base import TypedObject
    from ..func import fun

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
    from ..base import Object
    from ..class_ import class_

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


def getname(obj: "Object | type[Object]"):
    """Get the name of the object in the context of MyLang, if any."""
    from ..complex import String
    from ..func import fun

    if isinstance(obj, fun):
        return obj.name
    if hasattr(obj, "_m_name_"):
        return String(obj._m_name_)
    elif hasattr(obj, "__name__"):
        from ..complex import String

        return String(obj.__name__)
    else:
        return None


def iter_(obj: "Object"):
    """Get an iterator for the object in the context of MyLang."""
    if hasattr(obj, "__iter__"):
        return iter(obj)
    else:
        raise NotImplementedError(f"Object {obj} is not iterable in MyLang")


def repr_(obj: "Object | type[Object]") -> "String":
    """Get the string representation of the object in the context of MyLang."""
    from ..complex import String
    from ..base import Object, TypedObject

    if isinstance(obj, type):
        return String(f"<class {getname(obj)}>")
    if hasattr(obj, "_m_repr_"):
        try:
            return obj._m_repr_()
        except NotImplementedError as e:
            pass
    elif isinstance(obj, TypedObject) and hasattr(obj.type_, "_m_repr_"):
        try:
            return obj.type_._m_repr_(obj)
        except NotImplementedError:
            pass
    return String(f"{{TODO: str: {obj!r}}}")


def str_(obj: "Object | type[Object]") -> "String":
    from ..complex import String
    from ..base import TypedObject

    if isinstance(obj, type):
        return String(f"<class {getname(obj)}>")
    elif hasattr(obj, "_m_str_"):
        try:
            return obj._m_str_()
        except NotImplementedError:
            pass
    elif isinstance(obj, TypedObject) and hasattr(obj.type_, "_m_str_"):
        try:
            return obj.type_._m_str_(obj)
        except NotImplementedError:
            pass
    elif hasattr(obj, "_m_repr_"):
        try:
            return repr_(obj)
        except NotImplementedError:
            pass
    elif isinstance(obj, TypedObject) and hasattr(obj.type_, "_m_repr_"):
        try:
            return obj.type_._m_repr_(obj)
        except NotImplementedError:
            pass

    return String(f"{{TODO: str: {obj!r}}}")

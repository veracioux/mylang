from typing import Any, Literal

from .func import StatementList, fun, get
from . import undefined
from ._context import current_stack_frame, LocalsDict
from ._utils import (
    FunctionAsClass,
    Special,
    expose,
    expose_class_attr,
    function_defined_as_class,
    isinstance_,
    python_obj_to_mylang,
    set_contextvar,
    currently_called_func,
)
from .base import Args, Object, TypedObject
from .complex import String

__all__ = ("class_",)


class _Symbols:
    CURRENT_CLASS = type("CURRENT_CLASS", (object,), {})
    """Key for class that is currently being defined."""


@expose
@function_defined_as_class
@expose_class_attr("init")
class class_(Object, FunctionAsClass):
    _m_name_ = Special._m_name_("class")

    def __init__(self, name: Any, *rest: Any):
        # TODO: Validate args
        super().__init__(name, *rest)
        self.name = python_obj_to_mylang(name)
        self.bases: tuple[class_] = tuple(
            get(key) for key in rest[:-1]
        ) or (Object,)

        @python_obj_to_mylang
        def _default_initializer(*args, **kwargs):
            return undefined

        self.initializer = Method(_default_initializer)  # TODO: determine default initializer

        # Execute the body in the caller's lexical scope
        stack_frame = current_stack_frame.get()
        stack_frame.inherit_parent_lexical_scope()
        body = rest[-1]
        assert isinstance(body, StatementList), "class body must be a StatementList"
        stack_frame.lexical_scope.custom_data[_Symbols.CURRENT_CLASS] = self
        body.execute()

        if stack_frame.parent is not None:
            # Bind the class value under class name as key in caller's lexical scope
            stack_frame.parent.locals[self.name] = self

        locals_ = stack_frame.lexical_scope.locals
        # TODO: Make prototype a Dict
        # TODO: Rename LocalsDict to IdentityDict
        self.prototype = LocalsDict({
            k: (Method(v) if isinstance(v, fun) else v) for k, v in locals_.dict().items()
        })

    @classmethod
    @Special._m_classcall_
    def _m_classcall_(cls, args, /):
        """Create a class."""
        assert args.is_positional_only(), "class arguments must be positional only"
        assert len(args) >= 2
        assert isinstance(
            args[-1], StatementList
        ), "The last argument to class must be a StatementList"
        created_class = super().__new__(cls)
        created_class.__init__(*args[:])

        return created_class

    @Special._m_call_
    def _m_call_(self, args: Args, /) -> TypedObject:
        """Initialize an instance of the class."""
        # TODO: Define constructor and call it
        obj = TypedObject(self)
        self.initializer.bind(obj)(args)
        return obj

    @classmethod
    def init(cls, *mylang_args, **kwargs):
        mylang_args = Args(*mylang_args, **kwargs)
        with cls._caller_stack_frame() as stack_frame:
            created_class: class_ = stack_frame.lexical_scope.custom_data[
                _Symbols.CURRENT_CLASS
            ]
            created_class.initializer = Method(fun(String("initializer"), mylang_args))

    def _m_repr_(self):
        return String(f"<class {self.name}>")


class_.init = python_obj_to_mylang(class_.init)


class Method(Object):
    """A function defined in a class's initialization block, that is not bound
    to any object."""
    def __init__(self, func: fun):
        self.func = func
        super().__init__(func)

    def bind(self, bound_to: Object) -> "BoundMethod":
        return BoundMethod(bound_to, self.func)


class BoundMethod(fun):
    def __init__(self, bound_to: Object, func: fun, /):
        assert isinstance(bound_to, Object), f"{BoundMethod} first argument must be an Object"
        assert isinstance_(func, fun), f"{BoundMethod.__name__} second argument must be a function"
        self.self = bound_to
        self.func = func
        super().__init__(func.name, func.parameters, func.body)

    @classmethod
    @Special._m_classcall_
    def _m_classcall_(cls, args: Args, /) -> Any:
        bound_to = args[0]
        func = args[1]
        obj = Object.__new__(cls)
        obj.__init__(bound_to, func)
        return obj

    @Special._m_call_
    def _m_call_(self, args: Args, /) -> Any:
        # Inject `self` into the function's lexical scope
        current_stack_frame.get().locals["self"] = self.self
        if isinstance(self.func, type):
            python_callable = self.func._m_classcall_
        else:
            python_callable = self.func._m_call_
        with set_contextvar(currently_called_func, python_callable):
            return python_callable(args)


class Doc(Object):
    pass


class doc(Object, FunctionAsClass):
    _m_name_ = Special._m_name_("doc")

    @classmethod
    @Special._m_classcall_
    def _m_classcall_(cls, args: Args, /) -> String:
        assert (
            args.is_positional_only and len(args) == 1
        ), "doc takes exactly one positional argument"
        obj = args[0]
        assert isinstance(obj, Object), "doc argument must be an Object"
        docstring = getattr(obj, "__doc__", "")
        return String(docstring if docstring is not None else "")

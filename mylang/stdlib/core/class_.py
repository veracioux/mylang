from typing import Any

from mylang.stdlib.core.func import StatementList, fun
from . import undefined
from ._utils import (
    FunctionAsClass,
    Special,
    expose,
    expose_class_attr,
    function_defined_as_class,
    python_obj_to_mylang,
)
from .base import Args, Object, Dict, TypedObject
from .complex import String
from ._context import current_stack_frame

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
        self.bases = rest[:-1] or (Object,)
        self.initializer = python_obj_to_mylang(
            lambda: undefined
        )  # TODO: determine default initializer

        # Execute the body in the caller's lexical scope
        stack_frame = current_stack_frame.get()
        stack_frame.set_parent_lexical_scope(stack_frame.parent.lexical_scope)
        body = rest[-1] if rest else StatementList()
        stack_frame.lexical_scope.custom_data[_Symbols.CURRENT_CLASS] = self
        body.execute()

        # Bind the class value under class name as key in caller's lexical scope
        stack_frame.parent.locals[self.name] = self

        locals_ = stack_frame.lexical_scope.locals
        self.prototype = Dict.from_dict(locals_.dict())

    @classmethod
    @Special._m_classcall_
    def _m_classcall_(cls, args, /):
        """Create a class."""
        assert len(args) == 2 or (len(args) >= 4 and args[1] == String("is"))
        assert len(args) == 2 or isinstance(
            args[-1], StatementList
        ), "The last argument to class must be a StatementList"
        # Remove the 'is' if present
        if len(args) >= 4:
            args = args[:2] + args[3:-1]
        created_class = super().__new__(cls)
        created_class.__init__(*args[:])

        return created_class

    @Special._m_call_
    def _m_call_(self, args: Args, /) -> TypedObject:
        """Initialize an instance of the class."""
        # TODO: Define constructor and call it
        obj = TypedObject(self)
        self.initializer(args)
        return obj

    @classmethod
    def init(cls, *args, **kwargs):
        args = Args(*args, **kwargs)
        with current_stack_frame.get().parent as stack_frame:
            created_class = stack_frame.lexical_scope.custom_data[
                _Symbols.CURRENT_CLASS
            ]
            created_class.initializer = fun(Args(String("initializer")) + args)

    def _m_repr_(self):
        return String(f"<class {self.name}>")


class_.init = python_obj_to_mylang(class_.init)


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

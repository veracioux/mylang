"""Context module for MyLang standard library."""

from typing import Optional
from weakref import WeakKeyDictionary

from ._context import StackFrame

from ._utils import FunctionAsClass, function_defined_as_class, getattr_, python_obj_to_mylang, require_parent_locals, expose, expose_class_attr, require_parent_stack_frame
from .base import Dict, Object


_stack_frame_to_context: WeakKeyDictionary["StackFrame", "Context"] = WeakKeyDictionary()


class Context(Dict):
    """Holds context-specific data."""
    __slots__ = ("parent",)

    def __init__(self, parent: "Optional[Context]" = None):
        super().__init__()
        self.parent: "Optional[Context]" = parent

    def _m_getattr_(self, key):
        value = self._m_dict_.get(key)
        if value is not None:
            return value
        assert self.parent is not None, "Key not found in context"
        return getattr_(self.parent, key)


@expose
@function_defined_as_class()
@expose_class_attr("get")
class context(Object, FunctionAsClass):
    _CLASSCALL_SHOULD_RECEIVE_NEW_STACK_FRAME = True

    @classmethod
    def _m_classcall_(cls, args, /) -> Context:
        assert len(args) == 1, f"context takes exactly one argument ({len(args)} given)"
        key = args[0]
        stack_frame = require_parent_stack_frame()
        existing_context_in_current_stack_frame = _stack_frame_to_context.get(stack_frame)
        if existing_context_in_current_stack_frame is not None:
            context = existing_context_in_current_stack_frame
        else:
            context = Context(parent=cls.get())
            _stack_frame_to_context[stack_frame] = context
        require_parent_locals()[key] = context
        return context

    @classmethod
    def get(cls):
        """Get the current context."""
        stack_frame = require_parent_stack_frame()
        while stack_frame is not None:
            context = _stack_frame_to_context.get(stack_frame)
            if context is not None:
                return context
            stack_frame = stack_frame.parent

        return Context()


context.get = python_obj_to_mylang(context.get)  # type: ignore

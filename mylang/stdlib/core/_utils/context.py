from typing import TYPE_CHECKING, Optional


if TYPE_CHECKING:
    from .._context import StackFrame, LexicalScope, LocalsDict


def require_parent_stack_frame() -> "StackFrame":
    """Get the parent stack frame of the current stack frame."""
    from .._context import current_stack_frame

    parent = current_stack_frame.get().parent
    assert parent is not None, "No parent stack frame"
    return parent


def require_parent_lexical_scope() -> Optional["LexicalScope"]:
    """Get the parent lexical scope of the current stack frame."""
    parent_frame = require_parent_stack_frame()
    return parent_frame.lexical_scope if parent_frame is not None else None


def require_parent_locals() -> "LocalsDict":
    """Get the locals of the parent stack frame."""
    return require_parent_stack_frame().locals

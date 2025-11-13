"""Internal context, not exposed to MyLang."""

from contextlib import contextmanager
import dataclasses
from typing import TYPE_CHECKING, Any, Optional, TypeVar

from ._utils.types import IdentityDict
from .base import Object
from contextvars import ContextVar


if TYPE_CHECKING:
    from .func import StatementList
    from ._utils import AnyObject


class LocalsDict(IdentityDict[Any, "AnyObject"]):
    def __contains__(self, key, /) -> bool:
        from ._utils import python_obj_to_mylang

        return self._KeyWrapper(python_obj_to_mylang(key)) in self._dict

    def __getitem__(self, key, /):
        from ._utils import python_obj_to_mylang

        return self._dict[self._KeyWrapper(python_obj_to_mylang(key))]

    def __setitem__(self, key, value, /):
        from ._utils import python_obj_to_mylang

        self._dict[self._KeyWrapper(python_obj_to_mylang(key))] = value


class LexicalScope:
    """A linked list of local variable dictionaries.

    It represents all the key-value pairs available in the current lexical scope.
    """

    __slots__ = ("locals", "parent", "custom_data")

    def __init__(
        self,
        locals_: LocalsDict,
        parent: Optional["LexicalScope"] = None,
    ):
        self.locals = locals_
        self.parent = parent

        # TODO: Move to StackFrame
        self.custom_data: dict[Any, Any] = {}
        """A dictionary for storing custom data related to this lexical scope.

        Useful for context flow statements to communicate with each other.
        """

    def __getitem__(self, key: Any) -> "AnyObject":
        from ._utils import python_obj_to_mylang

        key = python_obj_to_mylang(key)
        if key in self.locals:
            return self.locals[key]
        elif self.parent is not None:
            return self.parent[key]
        else:
            raise KeyError(f"Key {key!r} not found in lexical scope.")

    def add_above(self, locals_: LocalsDict) -> "LexicalScope":
        """Create a new lexical scope with the given locals and insert it above
        this one."""
        current_parent = self.parent
        new_scope = LexicalScope(locals_, parent=current_parent)
        self.parent = new_scope
        return new_scope


@dataclasses.dataclass
class CatchSpec:
    """Specification for a catch block in MyLang.

    Example:
    catch error_key (
        body
    )
    """

    error_key: Optional[Object]
    body: "StatementList"


class StackFrame:
    __slots__ = (
        "locals",
        "parent",
        "lexical_scope",
        "return_value",
        "depth",
        "catch_spec",
        "_reset_token",
        "__weakref__",
    )

    def __init__(
        self,
        locals_: Optional[LocalsDict] = None,
        parent: Optional["StackFrame"] = None,
        lexical_scope: Optional[LexicalScope] = None,
    ):
        # TODO: Make readonly
        self.locals = locals_ or LocalsDict()
        self.parent = parent
        self.lexical_scope = lexical_scope or LexicalScope(
            self.locals,
            parent=None,
        )
        self.return_value: Optional[Object] = None
        self.depth = self.parent.depth + 1 if self.parent is not None else 0
        self.catch_spec: Optional[CatchSpec] = None
        self._reset_token = None
        """The reset token for the context variable."""

    def set_parent_lexical_scope(self, parent: Optional[LexicalScope]):
        """Set the parent lexical scope of this stack frame's lexical scope."""
        self.lexical_scope.parent = parent

    def inherit_parent_lexical_scope(self):
        """Set the parent lexical scope to the lexical scope of its parent
        stack frame."""
        if self.parent is not None:
            self.set_parent_lexical_scope(self.parent.lexical_scope)

    def __getitem__(self, key: Any) -> "AnyObject":
        return self.lexical_scope[key]

    def __enter__(self):
        if current_stack_frame.get() is self:
            raise RuntimeError("Stack frame is already the current stack frame.")
        self._reset_token = current_stack_frame.set(self)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        _ = exc_type, exc_value, traceback
        if self._reset_token is not None:
            current_stack_frame.reset(self._reset_token)
            self._reset_token = None

    def __repr__(self):
        return f"StackFrame(depth={self.depth})"


current_stack_frame = ContextVar[StackFrame]("stack_frame", default=None)  # type: ignore
"""The current stack frame."""


internal_module_bridge = ContextVar[LexicalScope | None](
    "internal_module_bridge",
    default=None,
)
"""In case a stdlib module is implemented both in Python and in MyLang,
this variable holds the value exported from the MyLang implementation.

The Python implementation can then use this variable to access that value.

The MyLang implementation will receive a _python variable injected into its
lexical scope, holding a proxy to the Python module.

Example:
# /path/to/stdlib/package/module.my
fun mylang_function() {
    echo Hello from MyLang
    _python.python_function()
)
return {a=1 b=2}
# /path/to/stdlib/package/module.py
from mylang import internal_module_bridge
internal_module_bridge.get().mylang_function()
def python_function():
    print("Hello from Python")
"""


TypeContextVarValue = TypeVar("TypeContextVarValue")


@contextmanager
def nested_stack_frame(locals_: Optional[LocalsDict] = None, lexical_scope: Optional[LexicalScope] = None):
    this_stack_frame = current_stack_frame.get()
    with StackFrame(locals_, parent=this_stack_frame, lexical_scope=lexical_scope) as new_stack_frame:
        yield new_stack_frame

from contextlib import contextmanager
from typing import Any, Optional, Sequence, TypeVar, Union

from mylang.stdlib.core._utils import python_obj_to_mylang
from .base import Object
from contextvars import ContextVar


TypeIdentityDictKey = TypeVar("TypeIdentityDictKey", bound=Object)
TypeIdentityDictValue = TypeVar("TypeIdentityDictValue", bound=Object)


class LocalsDict:
    """A dictionary that uses object identity (is) instead of hash and equality (==) for keys."""

    __slots__ = ("_dict",)

    class _KeyWrapper:
        __slots__ = ("key",)

        def __init__(self, key: TypeIdentityDictKey, /):
            self.key = key

        def __hash__(self):
            return id(self.key)

        def __eq__(self, other):
            return self.key is other.key

    def __init__(self, items_or_dict: Union[dict, Sequence[tuple]] = (), /):
        items = (
            items_or_dict.items() if isinstance(items_or_dict, dict) else items_or_dict
        )
        self._dict: dict["LocalsDict._KeyWrapper", TypeIdentityDictValue] = {
            (
                self._KeyWrapper(key)
                if not isinstance(key, LocalsDict._KeyWrapper)
                else key
            ): value
            for key, value in items
        }

    def __contains__(self, key: Any, /) -> bool:
        return self._KeyWrapper(python_obj_to_mylang(key)) in self._dict

    def __getitem__(self, key: Any, /):
        return self._dict[self._KeyWrapper(python_obj_to_mylang(key))]

    def __setitem__(self, key: Any, value: TypeIdentityDictValue, /):
        self._dict[self._KeyWrapper(python_obj_to_mylang(key))] = value

    def __repr__(self):
        return f"{self.__class__.__name__}({self.dict()!r})"

    def dict(self):
        return {k.key: v for k, v in self._dict.items()}

    def values(self):
        return self._dict.values()

    def __eq__(self, other: object) -> bool:
        if isinstance(other, LocalsDict):
            return self._dict == other._dict
        elif isinstance(other, dict):
            return self == self.__class__(other)
        else:
            return False


class LexicalScope:
    __slots__ = ("locals", "parent", "last_called_function", "custom_data")

    def __init__(
        self,
        locals_: LocalsDict,
        parent: Optional["LexicalScope"] = None,
    ):
        self.locals = locals_
        self.parent = parent
        # TODO: Instead of an object reference, consider using some sort of
        # `ref`-related mechanism that respects advice.
        self.last_called_function: Optional[Object] = None
        """The last function called in this lexical scope, if any.

        Useful for control flow statements, e.g. `else` to check if it follows
        an `if`.
        """

        # TODO: Move to StackFrame
        self.custom_data = {}
        """A dictionary for storing custom data related to this lexical scope.

        Useful for context flow statements to communicate with each other.
        """

    def __getitem__(self, key: Any) -> Object:
        key = python_obj_to_mylang(key)
        if key in self.locals:
            return self.locals[key]
        elif self.parent is not None:
            return self.parent[key]
        else:
            raise KeyError(f"Key {key!r} not found in lexical scope.")


class StackFrame:
    __slots__ = (
        "locals",
        "parent",
        "lexical_scope",
        "return_value",
        "depth",
        "_reset_token",
    )

    def __init__(
        self,
        locals_: LocalsDict = None,
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
        self._reset_token = None
        """The reset token for the context variable."""

    def set_parent_lexical_scope(self, parent: Optional[LexicalScope]):
        """Set the parent lexical scope of this stack frame's lexical scope."""
        self.lexical_scope.parent = parent

    def __getitem__(self, key: Any) -> Object:
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


current_stack_frame = ContextVar[StackFrame]("stack_frame", default=None)
"""The current stack frame."""


TypeContextVarValue = TypeVar("TypeContextVarValue")


@contextmanager
def _change_context_var(
    context_var: ContextVar[TypeContextVarValue], value: TypeContextVarValue
):
    """Switch the current context to the given context."""
    reset_token = context_var.set(value)

    try:
        yield value
    finally:
        context_var.reset(reset_token)


@contextmanager
def nested_stack_frame(
    locals_: LocalsDict = None, lexical_scope: Optional[LexicalScope] = None
):
    this_stack_frame = current_stack_frame.get()
    with StackFrame(
        locals_, parent=this_stack_frame, lexical_scope=lexical_scope
    ) as new_stack_frame:
        yield new_stack_frame

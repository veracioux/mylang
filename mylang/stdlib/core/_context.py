from contextlib import contextmanager
from typing import Any, Generic, Optional, Sequence, TypeVar, Union

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
        items = items_or_dict.items() if isinstance(items_or_dict, dict) else items_or_dict
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

    def __eq__(self, other: object) -> bool:
        if isinstance(other, LocalsDict):
            return self._dict == other._dict
        elif isinstance(other, dict):
            return self == self.__class__(other)
        else:
            return False


class LexicalScope:
    def __init__(
        self,
        locals_: LocalsDict,
        parent: Optional["LexicalScope"] = None,
    ):
        self.locals = locals_
        self.parent = parent

    def __getitem__(self, key: Any) -> Object:
        key = python_obj_to_mylang(key)
        if key in self.locals:
            return self.locals[key]
        elif self.parent is not None:
            return self.parent[key]
        else:
            raise KeyError(f"Key {key!r} not found in lexical scope.")


class StackFrame:
    def __init__(
        self,
        locals_: LocalsDict = None,
        parent: Optional["StackFrame"] = None,
    ):
        # TODO: Make readonly
        self.locals = locals_ or LocalsDict()
        self.parent = parent
        self.lexical_scope = LexicalScope(
            self.locals, parent=None,
        )
        self.return_value: Optional[Object] = None
        self.depth = self.parent.depth + 1 if self.parent is not None else 0

    def set_parent_lexical_scope(self, parent: Optional[LexicalScope]):
        """Set the parent lexical scope of this stack frame's lexical scope."""
        self.lexical_scope.parent = parent

    def __getitem__(self, key: Any) -> Object:
        return self.lexical_scope[key]


current_stack_frame = ContextVar[StackFrame]("stack_frame", default=None)
"""The current stack frame."""


TypeContextVarValue = TypeVar("TypeContextVarValue")


@contextmanager
def _change_context_var(context_var: ContextVar[TypeContextVarValue], value: TypeContextVarValue):
    """Switch the current context to the given context."""
    reset_token = context_var.set(value)

    try:
        yield value
    finally:
        context_var.reset(reset_token)


@contextmanager
def nested_stack_frame(locals_: LocalsDict = None, /):
    this_stack_frame = current_stack_frame.get()
    with _change_context_var(
        current_stack_frame, StackFrame(locals_, parent=this_stack_frame)
    ) as new_stack_frame:
        yield new_stack_frame


@contextmanager
def parent_stack_frame():
    """Switch to the parent context of the current context."""
    this_stack_frame = current_stack_frame.get()
    if this_stack_frame.parent is None:
        raise RuntimeError("No parent stack frame available.")

    with _change_context_var(current_stack_frame, this_stack_frame.parent) as new_stack_frame:
        yield new_stack_frame

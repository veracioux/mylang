from contextlib import contextmanager
from typing import Any, Optional

from mylang.stdlib.core._utils import python_obj_to_mylang
from .base import Object
from contextvars import ContextVar


class Context:
    def __init__(
        self,
        dict_: Optional[dict[Object, Object]] = {},
        /,
        *,
        parent: Optional["Context"] = None,
    ):
        super().__init__()
        self.parent = parent
        self.dict_: dict[int, Object] = {id(key): value for key, value in dict_.items()}
        """Maps the key ID instead of the key itself, so keys can
        be looked up by identity (is) instead of equality (==)."""

    def __contains__(self, key: Object) -> bool:
        if id(key) in self.dict_:
            return True
        elif self.parent is not None:
            return key in self.parent
        else:
            return False

    def __getitem__(self, key: Any) -> Object:
        id_ = id(python_obj_to_mylang(key))
        if id_ in self.dict_:
            return self.dict_[id_]
        elif self.parent is not None:
            return self.parent[key]
        else:
            raise KeyError(f"Key {key!r} not found in context.")

    def __setitem__(self, key: Any, value: Any) -> None:
        self.dict_[id(python_obj_to_mylang(key))] = python_obj_to_mylang(value)

    def __repr__(self):
        import ctypes
        dict_repr = '{' + ', '.join(
            f'{ctypes.cast(key, ctypes.py_object).value!r}: {value!r}'
            for key, value in self.dict_.items()
        ) + '}'
        return f'{self.__class__.__name__}({dict_repr}, parent={self.parent!r})'

class Application(Context):
    pass


current_context = ContextVar[Context]("current_context", default=Context())


@contextmanager
def nested_context(dict_: dict[Object, Object]):
    this_context = current_context.get()
    new_context = Context(dict_, parent=this_context)
    reset_token = current_context.set(new_context)
    try:
        yield new_context
    finally:
        current_context.reset(reset_token)

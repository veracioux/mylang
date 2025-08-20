import functools
from typing import Any

from .base import Args, Object


__all__ = ('String', 'Path')


class String(Object):
    @functools.cache
    def __new__(cls, *args, **kwargs):
        return super().__new__(cls)

    def __init__(self, value: str = ""):
        self.value = value
        super().__init__()

    def _m_init_(self, value: str = ""):
        pass

    def _m_repr_(self):
        return String(repr(self.value))

    def __eq__(self, other: Any):
        return isinstance(other, self.__class__) and self.value == other.value

    def __hash__(self):
        return hash(self.value)

    def __repr__(self):
        return f'{self.__class__.__name__}({self.value!r})'

    def __str__(self):
        return self.value


class Path(Object):
    def __init__(self, *args):
        super().__init__(*args)

    def _m_init_(self, args: Args, /):
        self.parts = args._m_dict_

from typing import Any
from .base import class_, Object


class String(Object):
    def __init__(self, value: str = ""):
        self.value = value
        super().__init__()

    def _m_init_(self, value: str = ""):
        pass

    def __eq__(self, other: Any):
        return isinstance(other, self.__class__) and self.value == other.value

    def __hash__(self):
        return hash(self.value)

    def __repr__(self):
        return f'{self.__class__.__name__}({self.value!r})'


# class Path(metaclass=class_):
#     def __mylang_init__(self, parts: List[String]):
#         pass


class Context(Object):
    pass


class Application(Context):
    pass

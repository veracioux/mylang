from abc import ABC
from typing import Generic, TypeVar, final
from .base import Object
import functools


TypeValue = TypeVar("TypeValue")


class Primitive(Object):
    @functools.cache
    def __new__(cls, *args):
        return super().__new__(cls)


class Scalar(Primitive, Generic[TypeValue]):
    __slots__ = ("value",)

    def __init__(self, value: TypeValue, /):
        self.value = value

    def __eq__(self, other):
        return (isinstance(other, Scalar) and self.value == other.value) or (
            other == self.value
        )

    def __bool__(self):
        return bool(self.value)

    def __hash__(self):
        return hash(self.value)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.value!r})"

    def _m_repr_(self):
        from .complex import String
        return String(repr(self.value))


class Number(Scalar[TypeValue], Generic[TypeValue]):
    pass


class Int(Number[int]):
    pass


class Float(Number[float]):
    pass


class Bool(Scalar[bool]):
    def _m_repr_(self):
        return "true" if self.value else "false"


class Empty(Primitive, ABC):
    def __bool__(self):
        return False


@final
class Null(Empty):
    def _m_repr_(self):
        return "null"


@final
class Undefined(Empty):
    def _m_repr_(self):
        return "undefined"


# TODO: uncomment
null = Null()
undefined = Undefined()
true = Bool(True)
false = Bool(False)

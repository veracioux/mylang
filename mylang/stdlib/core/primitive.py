from abc import ABC
from typing import Generic, TypeVar, final

from ._utils import Special
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

    def __str__(self):
        return str(self._m_str_())

    @Special._m_str_
    def _m_str_(self):
        from .complex import String
        return String(str(self.value))

    @Special._m_repr_
    def _m_repr_(self):
        from .complex import String
        return String(repr(self.value))


class Number(Scalar[TypeValue], Generic[TypeValue]):
    def __sub__(self, other: 'Number'):
        return self.__class__(self.value - other.value)

    def __add__(self, other: 'Number'):
        return self.__class__(self.value + other.value)

    def __mul__(self, other: 'Number'):
        return self.__class__(self.value * other.value)

    def __truediv__(self, other: 'Number'):
        if other.value == 0:
            raise ZeroDivisionError("division by zero")
        return self.__class__(self.value / other.value)

    def __int__(self):
        return int(self.value)

    def __float__(self):
        return float(self.value)


class Int(Number[int]):
    pass


class Float(Number[float]):
    pass


class Bool(Scalar[bool]):
    @Special._m_repr_
    def _m_repr_(self):
        return "true" if self.value else "false"

    @Special._m_str_
    def _m_str_(self):
        return self._m_repr_()


class Empty(Primitive, ABC):
    def __bool__(self):
        return False


@final
class Null(Empty):
    @Special._m_repr_
    def _m_repr_(self):
        return "null"


@final
class Undefined(Empty):
    @Special._m_repr_
    def _m_repr_(self):
        return "undefined"


# TODO: uncomment
null = Null()
undefined = Undefined()
true = Bool(True)
false = Bool(False)

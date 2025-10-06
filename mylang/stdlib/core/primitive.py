"""Primitive types for mylang.

This module defines the basic primitive types including scalars, numbers,
booleans, and special values like undefined and null.
"""

from abc import ABC
from typing import Generic, TypeVar, final

from ._utils import expose, str_, repr_

from .base import Object
import functools


TypeValue = TypeVar("TypeValue")


@expose
class Primitive(Object):
    # TODO: Use weak caching
    @functools.cache
    def __new__(cls, *args):
        return super().__new__(cls)


@expose
class Scalar(Primitive, Generic[TypeValue]):
    __slots__ = ("value",)

    def __init__(self, value: TypeValue, /):
        self.value = value

    def __eq__(self, other):
        return (isinstance(other, Scalar) and self.value == other.value) or (other == self.value)

    def __bool__(self):
        return bool(self.value)

    def __hash__(self):
        return hash(self.value)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.value!r})"

    def __str__(self):
        return str_(self).value

    def _m_str_(self):
        from .complex import String

        return String(str(self.value))

    def _m_repr_(self):
        from .complex import String

        return String(repr(self.value))


@expose
class Number(Scalar[TypeValue], Generic[TypeValue]):
    def __sub__(self, other: "Number"):
        return self.__class__(self.value - other.value)

    def __add__(self, other: "Number"):
        return self.__class__(self.value + other.value)

    def __mul__(self, other: "Number"):
        return self.__class__(self.value * other.value)

    def __truediv__(self, other: "Number"):
        if other.value == 0:
            raise ZeroDivisionError("division by zero")
        return self.__class__(self.value / other.value)

    def __gt__(self, other: "Number"):
        return Bool(self.value > other.value)

    def __ge__(self, other: "Number"):
        return Bool(self.value >= other.value)

    def __lt__(self, other: "Number"):
        return Bool(self.value < other.value)

    def __le__(self, other: "Number"):
        return Bool(self.value <= other.value)

    def __int__(self):
        return int(self.value)

    def __float__(self):
        return float(self.value)


@expose
class Int(Number[int]):
    pass


@expose
class Float(Number[float]):
    pass


@expose
class Bool(Scalar[bool]):
    def _m_repr_(self):
        from .complex import String
        return String("true" if self.value else "false")
    def _m_str_(self):
        return repr_(self)

@expose
class Empty(Primitive, ABC):
    def __bool__(self):
        return False


@expose
@final
class Null(Empty):
    def _m_repr_(self):
        return "null"


@expose
@final
class Undefined(Empty):
    def _m_repr_(self):
        return "undefined"


null = Null()
undefined = Undefined()
true = Bool(True)
false = Bool(False)

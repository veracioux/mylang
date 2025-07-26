from abc import ABC
from typing import Generic, TypeVar, final
from .base import Object
import functools


TypeValue = TypeVar("TypeValue")


class Primitive(Object):
    pass


class Scalar(Primitive, Generic[TypeValue]):
    __slots__ = ("value",)

    def __init__(self, value: TypeValue):
        self.value = value

    def __eq__(self, other):
        return (isinstance(other, Scalar) and self.value == other.value) or (
            other == self.value
        )

    def __hash__(self):
        return hash(self.value)

    def __repr__(self):
        return f'{self.__class__.__name__}({self.value!r})'


class Number(Scalar[TypeValue], Generic[TypeValue]):
    pass


class Int(Number[int]):
    pass


class Float(Number[float]):
    pass


class Bool(Scalar[bool]):
    pass


class Empty(Primitive, ABC):
    pass


@final
class Null(Empty):
    # Make Null a singleton
    @functools.lru_cache(maxsize=1)
    def __new__(cls):
        return super().__new__(cls)


@final
class Undefined(Empty):
    # Make Null a singleton
    @functools.lru_cache(maxsize=1)
    def __new__(cls):
        return super().__new__(cls)


# TODO: uncomment
null = Null()
undefined = Undefined()
true = Bool(True)
false = Bool(False)

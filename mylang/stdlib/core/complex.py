import functools
from typing import Any

from ._utils import expose, repr_, str_

from .base import Args, Object


@expose
class String(Object):
    # TODO: Use weak caching
    @functools.cache
    def __new__(cls, *args, **kwargs):
        return super().__new__(cls)

    def __init__(self, value: str = ""):
        self.value = value if isinstance(value, str) else str(value)
        super().__init__()

    def _m_init_(self, value: str = ""):
        pass

    def _m_repr_(self):
        return String(repr(self.value))

    def _m_str_(self):
        return self

    def __eq__(self, other: Any):
        return (isinstance(other, self.__class__) and self.value == other.value) or (
            isinstance(other, str) and self.value == other
        )

    def __hash__(self):
        return hash(self.value)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.value!r})"

    def __str__(self):
        return self.value


@expose
class Path(Object):
    def __init__(self, *args):
        super().__init__(*args)

    def _m_init_(self, args: Args, /):
        assert args.is_positional_only, "Path takes only positional arguments"
        assert len(args) > 1, "Path must have at least two parts"
        self.parts: tuple[Object] = tuple(args[:])

    def __repr__(self):
        return f"{self.__class__.__name__}({', '.join(repr(part) for part in self.parts)})"

    def _m_repr_(self):
        string = ".".join(repr_(part).value for part in self.parts)
        slice_ = slice(
            1 if isinstance(self.parts[0], Dots) else 0,
            -1 if isinstance(self.parts[-1], Dots) else len(string),
        )

        return String(string[slice_])

    def _m_str_(self):
        return String(".".join(str_(part).value for part in self.parts))


@expose
class Dots(Object):
    """Something like Python's ellipsis, but represents an arbitrary number of dots (1 or more)"""

    def __init__(self, count: int):
        assert count > 0, "Dots count must be positive"
        self.count = count

    def __eq__(self, value: object, /):
        return isinstance(value, Dots) and self.count == value.count

    def _m_repr_(self):
        return String("." * self.count)

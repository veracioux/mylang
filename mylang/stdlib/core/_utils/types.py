from types import ModuleType
from typing import TYPE_CHECKING, Any, Generic, Sequence, TypeVar, Union

from ..base import Object


if TYPE_CHECKING:
    from . import FunctionAsClass
    from .. import Error


AnyObject = Union[Object, "FunctionAsClass", type["FunctionAsClass"], "Error", type["Error"]]
"""A type that can represent any MyLang object, including functions defined as classes."""


class PythonModuleWrapper(Object):
    """Wraps a Python module to expose it to MyLang."""

    def __init__(self, module: ModuleType):
        self.module = module

    def _m_repr_(self):
        from ..complex import String
        # FIXME
        return String(f'<internal module {self.module.__name__}>')


class PythonContext:
    """Holds some privileged Python context for use by MyLang stdlib modules."""
    __slots__ = ("python_module")

    def __init__(self, python_module: ModuleType | None = None):
        self.python_module = python_module
        """The corresponding Python module of the current module being loaded."""

    def __getattr__(self, name):
        return getattr(self.python_module, name)

    def __setattr__(self, name, value):
        if name == "python_module":
            super().__setattr__(name, value)
        else:
            setattr(self.python_module, name, value)

    def __delattr__(self, name):
        delattr(self.python_module, name)


TypeIdentityDictKey = TypeVar("TypeIdentityDictKey")
TypeIdentityDictValue = TypeVar("TypeIdentityDictValue")


class IdentityDict(Generic[TypeIdentityDictKey, TypeIdentityDictValue]):
    """A dictionary that uses object identity (is) instead of hash and equality (==) for keys."""

    __slots__ = ("_dict",)

    class _KeyWrapper:
        __slots__ = ("key",)

        def __init__(self, key: Any, /):
            self.key = key

        def __hash__(self):
            return id(self.key)

        def __eq__(self, other):
            return self.key is other.key

    def __init__(self, items_or_dict: dict | Sequence[tuple] = (), /):
        items = items_or_dict.items() if isinstance(items_or_dict, dict) else items_or_dict
        self._dict: dict["IdentityDict._KeyWrapper", TypeIdentityDictValue] = {
            (self._KeyWrapper(key) if not isinstance(key, IdentityDict._KeyWrapper) else key): value
            for key, value in items
        }

    def __contains__(self, key: TypeIdentityDictKey, /) -> bool:
        return self._KeyWrapper(key) in self._dict

    def __getitem__(self, key: TypeIdentityDictKey, /):
        return self._dict[self._KeyWrapper(key)]

    def __setitem__(self, key: TypeIdentityDictKey, value: TypeIdentityDictValue, /):
        self._dict[self._KeyWrapper(key)] = value

    def __repr__(self):
        return f"{self.__class__.__name__}({self.dict()!r})"

    def dict(self):
        return {k.key: v for k, v in self._dict.items()}

    def values(self):
        return self._dict.values()

    def __eq__(self, other: object) -> bool:
        if isinstance(other, IdentityDict):
            return self._dict == other._dict
        elif isinstance(other, dict):
            return self == self.__class__(other)
        else:
            return False
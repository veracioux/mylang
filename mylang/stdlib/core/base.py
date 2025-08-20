import inspect
from typing import TYPE_CHECKING, Any, Generic, Iterable, TypeVar, final, overload

from ._utils import (
    mylang_obj_to_python,
    python_dict_from_args_kwargs,
    python_obj_to_mylang,
)

T = TypeVar("T", bound="Object")

if TYPE_CHECKING:
    from .complex import String


class Object:
    @overload
    def __init__(self, *args: "Object", **kwargs: "Object"): ...

    def __init__(self, *args: "Object", **kwargs: "Object"):
        if any(isinstance(arg, Args) for arg in args):
            if len(args) > 1:
                raise ValueError(
                    "If an argument of type Args is used, it must be the only argument."
                )
            self._m_init_(args[0])
        else:
            self._m_init_(Args.from_dict(python_dict_from_args_kwargs(*args, **kwargs)))

    def _m_init_(self, args: "Args", /):
        assert isinstance(args, Args)

    def _m_setattr_(self, key: "Object", value: "Object", /):
        assert False

    def __repr__(self):
        parameters = inspect.signature(self.__init__).parameters
        if all(
            x.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
            for x in parameters.values()
        ):
            return super().__repr__()
        initializers = {f"{k}={getattr(self, k)!r}" for k in parameters.keys()}
        return f"{self.__class__.__name__}({', '.join(initializers)})"

    def __str__(self):
        raise NotImplementedError("__str__ is not implemented for this object")

    def _m_repr_(self) -> "String":
        """Return a string representation of the object that will be used in the mylang context."""
        raise NotImplementedError("repr is not implemented for this object")

    def __hash__(self):
        return id(self)


# TODO: probably want class to be a typed object, but not sure how to do that
# because of circular dependencies
class class_(Object):
    pass


# TODO: Use later as base for bunch of classes
class TypedObject(Object):
    """Same as :class:`Object` but read/assignment is validated against the class definition."""


class Array(Object, Generic[T]):
    """An object that contains a sequence of objects."""

    def _m_init_(self, args: "Args", /):
        from .primitive import Int

        super()._m_init_(args)
        assert all(isinstance(k, Int) for k in args)
        self._m_array_: list[Object] = list(args._m_dict_.values())

    # TODO: Rename to from_iterable
    @classmethod
    def from_list(cls, source: list, /):
        obj = cls.__new__(cls)
        obj._m_array_ = [python_obj_to_mylang(x) for x in source]
        return obj

    def __eq__(self, other):
        """Check if two arrays are equal."""
        return (
            isinstance(other, self.__class__)
            and self._m_array_ == other._m_array_
            or isinstance(other, list)
            and self._m_array_ == other
        )

    def __iter__(self):
        return iter(self._m_array_)

    def __len__(self):
        return len(self._m_array_)

    @overload
    def __getitem__(self, key: slice, /) -> "Array": ...

    def __getitem__(self, key: Any, /) -> Object:
        result = self._m_array_[key]
        if isinstance(result, list):
            return Array.from_list(result)
        return result

    def __repr__(self):
        return f"{self.__class__.__name__}.from_list({self._m_array_!r})"

    def _m_repr_(self):
        from .complex import String

        return String(
            "("
            + "; ".join(str(x._m_repr_()) for x in self)
            + (";" if len(self) < 2 else "")
            + ")"
        )


class Dict(Object):
    """An object that contains a mapping of keys to values."""

    def _m_init_(self, args: "Args", /):
        super()._m_init_(args)
        self._m_dict_: dict[Object, Object] = args._m_dict_

    def _m_repr_(self):
        from .complex import String

        if len(self) == 0:
            return String("()")

        return String(
            "("
            + ", ".join(
                f"{k._m_repr_()}={v._m_repr_()}" for k, v in self._m_dict_.items()
            )
            + ")"
        )

    @classmethod
    def from_dict(cls, source: dict[Any, Any], /):
        obj = cls.__new__(cls)
        obj._m_dict_ = {
            python_obj_to_mylang(k): python_obj_to_mylang(v) for k, v in source.items()
        }
        return obj

    def __setattr__(self, name: str, value: Any, /) -> None:
        if name == "_m_dict_":
            super().__setattr__(name, value)
        else:
            from .complex import String

            try:
                getattr(self, "_m_dict_")
            except AttributeError:
                super().__setattr__("_m_dict_", {})
            self._m_dict_[String(name)] = python_obj_to_mylang(value)

    def __getattribute__(self, name: str, /) -> Any:
        if name == "_m_dict_":
            return super().__getattribute__("_m_dict_")
        else:
            from .complex import String

            key = String(name)
            if hasattr(self, "_m_dict_") and key in self._m_dict_:
                return self._m_dict_[key]
            else:
                return super().__getattribute__(name)

    def __len__(self):
        return len(self._m_dict_)

    def __iter__(self):
        """Iterate over the keys of the dictionary."""
        return iter(self._m_dict_)

    def __setitem__(self, key: Any, value: Any, /):
        return self._m_dict_.__setitem__(
            python_obj_to_mylang(key),
            python_obj_to_mylang(value),
        )

    def __getitem__(self, key: Any, /):
        return self._m_dict_.__getitem__(python_obj_to_mylang(key))

    def __repr__(self):
        get_from_dict_repr = (
            lambda: f"{self.__class__.__name__}.from_dict({mylang_obj_to_python(self._m_dict_)!r})"
        )
        return get_from_dict_repr()

    def __eq__(self, value: object, /) -> bool:
        return isinstance(value, self.__class__) and self._m_dict_ == value._m_dict_


# TODO: Check if there are any gaps in the positional argument indexes?
@final
class Args(Dict):
    """Represents an unpacked Dict.

    Right now it does nothing extra by itself, but various contexts treat it
    differently than :class:`Dict`.
    """

    def __new__(cls, *args: Any, **kwargs: Any):
        # Make Args(args) where isinstance(args, Args) return args
        if len(kwargs) == 0 and len(args) == 1 and isinstance(args[0], Args):
            return args[0]
        return super().__new__(cls)

    def get_last_positional_index(self):
        from .primitive import Int

        last_positional_arg_index = -1
        for key in self._m_dict_:
            if isinstance(key, Int):
                last_positional_arg_index = max(last_positional_arg_index, key.value)

        return last_positional_arg_index if last_positional_arg_index >= 0 else None

    def keyed_dict(self):
        """Get the keyed items (i.e. non-positional) of the Args."""
        from .primitive import Int

        return {k: v for k, v in self._m_dict_.items() if not isinstance(k, Int)}

    @overload
    def __getitem__(self, key: slice, /) -> Array: ...

    def __getitem__(self, key: Any, /) -> Object:
        """Get an item from the Args."""
        if isinstance(key, slice):
            from .primitive import Int

            positional_args = tuple(
                v for k, v in self._m_dict_.items() if isinstance(k, Int)
            )
            return Array.from_list(positional_args[key])
        else:
            return self._m_dict_[python_obj_to_mylang(key)]

    def __contains__(self, key: Any, /) -> bool:
        """Check if the Args contains a key."""
        return python_obj_to_mylang(key) in self._m_dict_

    def __add__(self, other: "Args" | Iterable, /) -> "Args":
        """Combine two Args objects."""
        if isinstance(other, self.__class__):
            positional = (*self[:], *other[:])
            return Args.from_dict(
                dict(enumerate(positional)) | self.keyed_dict() | other.keyed_dict()
            )
        elif isinstance(other, Iterable):
            positional = (*self[:], *other)
            return Args.from_dict(dict(enumerate(positional)) | self.keyed_dict())
        else:
            return NotImplemented

    def __radd__(self, other: Iterable, /):
        if not isinstance(other, Iterable):
            return NotImplemented
        positional = (*other, *self[:])
        return Args.from_dict(dict(enumerate(positional)) | self.keyed_dict())

    def _m_repr_(self):
        from .complex import String
        positional_args = self[:]
        keyed_args = self.keyed_dict()
        string = ", ".join(
            filter(
                lambda x: x,
                (
                    ", ".join(str(arg._m_repr_()) for arg in positional_args),
                    ", ".join(
                        f"{k._m_repr_()}={v._m_repr_()}" for k, v in keyed_args.items()
                    ),
                )
            )
        )
        if len(positional_args) == 1 and len(keyed_args) == 0:
            string += ","

        return String(string)

    def is_positional_only(self) -> bool:
        """Check if the Args contains only positional arguments."""
        return len(self) == len(self[:])

    def is_keyed_only(self) -> bool:
        """Check if the Args contains only keyed arguments."""
        return len(self) == len(self.keyed_dict())

    def is_mixed_positional_keyed(self) -> bool:
        """Check if the Args contains both positional and keyed arguments."""
        return not self.is_positional_only() and not self.is_keyed_only()
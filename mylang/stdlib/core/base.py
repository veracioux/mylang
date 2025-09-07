import abc
import copy
import inspect
from typing import TYPE_CHECKING, Any, Generic, Iterable, TypeVar, final, overload

from ._utils import (
    Special,
    mylang_obj_to_python,
    python_dict_from_args_kwargs,
    python_obj_to_mylang,
    set_contextvar,
)

T = TypeVar("T", bound="Object")

if TYPE_CHECKING:
    from .complex import String
    from .class_ import class_


class Object:
    @overload
    def __init__(self, *args: "Object", **kwargs: "Object"): ...

    def __init__(self, *args: "Object", **kwargs: "Object"):
        if any(isinstance(arg, Args) for arg in args):
            positional = []
            keyed = {}
            for arg in args:
                if isinstance(arg, Args):
                    positional += arg[:]
                    keyed |= arg.keyed_dict()
                else:
                    positional.append(arg)

            keyed |= kwargs

            self._m_init_(Args.from_dict(dict(enumerate(positional)) | keyed))
        else:
            self._m_init_(Args.from_dict(python_dict_from_args_kwargs(*args, **kwargs)))

    @Special._m_init_
    def _m_init_(self, args: "Args", /):
        assert isinstance(args, Args)

    @Special._m_setattr_
    def _m_setattr_(self, key: "Object", value: "Object", /):
        assert False

    def __repr__(self):
        parameters = inspect.signature(self.__init__).parameters
        if any(
            x.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
            for x in parameters.values()
        ):
            return super().__repr__()
        initializers = {f"{k}={getattr(self, k)!r}" for k in parameters.keys()}
        return f"{self.__class__.__name__}({', '.join(initializers)})"

    def __str__(self):
        if hasattr(self, Special._m_str_.name):
            return self._m_str_().value
        elif isinstance(self, TypedObject) and hasattr(self.type_, Special._m_str_.name):
            return self.type_._m_str_(self).value
        elif hasattr(self, Special._m_repr_.name):
            return str(self._m_repr_())
        else:
            raise NotImplementedError("__str__ is not implemented for this object")

    @Special._m_repr_
    def _m_repr_(self) -> "String":
        """Return a string representation of the object that will be used in the mylang context."""
        raise NotImplementedError("repr is not implemented for this object")

    def __hash__(self):
        return id(self)


class IncompleteExpression(abc.ABC):
    """An expression that needs some processing in order to produce a value."""

    @abc.abstractmethod
    def evaluate(self) -> Object:
        """Evaluate the expression recursively and get its value."""

    @staticmethod
    def evaluate_all_in_object(obj: Object):
        """Execute all `IncompleteExpression`s recursively in the given object, and replace each with the value it returned.

        The object and all its nested objects are NOT modified in-place.
        Instead, each object is copied, but only if needed (i.e. if any of its
        children need to be transformed).

        Note: A `StatementList` is a special case - it won't be evaluated.

        Returns:
            obj The possibly modified object.
        """
        from .func import StatementList

        if isinstance(obj, IncompleteExpression):
            return obj.evaluate()

        if isinstance(obj, StatementList):
            return obj

        dict_attributes = (
            "__dict__",
            *((Special._m_dict_.name,) if hasattr(obj, Special._m_dict_.name) else ()),
        )

        is_obj_copied = False

        # Iterate through all top-level items in __dict__ and _m_dict_ and
        # evaluate all incomplete expressions in the key and value, recursively
        for dict_attr in dict_attributes:
            if not hasattr(obj, dict_attr):
                continue

            dict_ = getattr(obj, dict_attr)
            is_dict_copied = False

            for key, value in tuple(dict_.items()):
                new_key = IncompleteExpression.evaluate_all_in_object(key)
                new_value = IncompleteExpression.evaluate_all_in_object(value)

                if new_key is not key or new_value is not value:
                    if not is_dict_copied:
                        dict_ = copy.copy(dict_)
                        is_dict_copied = True
                    if not is_obj_copied:
                        obj = copy.copy(obj)
                        is_obj_copied = True
                    if new_key is not key:
                        del dict_[key]
                    dict_[new_key] = new_value
                    setattr(obj, dict_attr, dict_)

        # Iterate through all items in _m_array_ and evaluate all incomplete
        # expressions in them, recursively
        if hasattr(obj, Special._m_array_.name):
            arr = getattr(obj, Special._m_array_.name)
            is_array_copied = False
            for i, item in enumerate(arr):
                new_item = IncompleteExpression.evaluate_all_in_object(item)
                if new_item is not item:
                    if not is_array_copied:
                        arr = copy.copy(arr)
                        is_array_copied = True
                    if not is_obj_copied:
                        obj = copy.copy(obj)
                        is_obj_copied = True
                    arr[i] = new_item
                    setattr(obj, Special._m_array_.name, arr)

        return obj


class Operation(Object, IncompleteExpression, abc.ABC):
    __slots__ = "operator"

    def __init__(self, operator: str):
        self.operator = operator

    def _call_op(self, *operands: Object):
        from .func import op
        from ._utils import currently_called_func
        from .complex import String

        with set_contextvar(currently_called_func, op._m_classcall_):
            return op._m_classcall_(Args(String(self.operator), *operands))


class UnaryOperation(Operation, abc.ABC):
    __slots__ = "operand"

    def __init__(self, operator: str, operand: Object):
        self.operator = operator
        self.operand = operand

    def evaluate(self):
        return self._call_op(self.evaluate_all_in_object(self.operand))


class PrefixOperation(UnaryOperation):
    pass


class PostfixOperation(UnaryOperation):
    pass


class BinaryOperation(Operation):
    __slots__ = "operands"

    def __init__(self, operator: str, operands: list[Object]):
        super().__init__(operator)
        self.operands = operands

    def evaluate(self):
        return self._call_op(
            *(self.evaluate_all_in_object(operand) for operand in self.operands)
        )


# TODO: Use later as base for bunch of classes
# TODO: Maybe rename to ClassInstance
class TypedObject(Object):
    """Same as :class:`Object` but read/assignment is validated against the class definition."""

    def __init__(self, type_: "class_"):
        self.type_ = type_
        self._m_dict_ = {}
        super().__init__(type_)

    @Special._m_repr_
    def _m_repr_(self):
        # TODO: Improve
        from .complex import String
        return String(f"<{self.type_.name} instance at {hex(id(self))}>")


class Array(Object, Generic[T]):
    """An object that contains a sequence of objects."""

    @Special._m_init_
    def _m_init_(self, args: "Args", /):
        super()._m_init_(args)
        assert args.is_positional_only()
        self._m_array_: list[Object] = list(args._m_dict_.values())

    # TODO: Rename to from_iterable
    @classmethod
    def from_iterable(cls, source: Iterable[T], /):
        obj = cls.__new__(cls)
        obj.__init__()
        obj._m_array_: list[T] = Special._m_array_([python_obj_to_mylang(x) for x in source])
        return obj

    def __eq__(self, other):
        """Check if two arrays are equal."""
        return (
            isinstance(other, self.__class__)
            and self._m_array_ == other._m_array_
            or isinstance(other, list)
            and self._m_array_ == other
        )

    def __add__(self, other: Iterable[T], /) -> "Array[T]":
        if not isinstance(other, Iterable):
            return NotImplemented
        return Array.from_iterable((*self._m_array_, *other))

    def __iter__(self) -> Iterable[T]:
        return iter(self._m_array_)

    def __len__(self):
        return len(self._m_array_)

    @overload
    def __getitem__(self, key: slice, /) -> "Array[T]": ...

    def __getitem__(self, key: Any, /) -> T:
        result = self._m_array_[key]
        if isinstance(result, list):
            return Array.from_iterable(result)
        return result

    def __repr__(self):
        return f"{self.__class__.__name__}.from_iterable({self._m_array_!r})"

    @Special._m_repr_
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

    @Special._m_init_
    def _m_init_(self, args: "Args", /):
        super()._m_init_(args)
        self._m_dict_: dict[Object, Object] = args._m_dict_.copy()

    @Special._m_repr_
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
        obj._m_dict_ = Special._m_dict_(
            {
                python_obj_to_mylang(k): python_obj_to_mylang(v)
                for k, v in source.items()
            }
        )
        return obj

    def __setattr__(self, name: str, value: Any, /) -> None:
        if name == Special._m_dict_.name:
            super().__setattr__(name, value)
        else:
            from .complex import String

            try:
                getattr(self, Special._m_dict_.name)
            except AttributeError:
                super().__setattr__(Special._m_dict_.name, {})
            self._m_dict_[String(name)] = python_obj_to_mylang(value)

    def __getattribute__(self, name: str, /) -> Any:
        if name == Special._m_dict_.name:
            return super().__getattribute__(Special._m_dict_.name)
        else:
            from .complex import String

            key = String(name)
            if hasattr(self, Special._m_dict_.name) and key in self._m_dict_:
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
        return f"{self.__class__.__name__}.from_dict({mylang_obj_to_python(self._m_dict_)!r})"

    def __eq__(self, value: object, /) -> bool:
        return isinstance(value, self.__class__) and self._m_dict_ == value._m_dict_


# TODO: Check if there are any gaps in the positional argument indexes?
@final
class Args(Dict):
    """Represents an unpacked Dict.

    Right now it does nothing extra by itself, but various contexts treat it
    differently than :class:`Dict`.
    """

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
            return Array.from_iterable(positional_args[key])
        else:
            from .primitive import Int

            if isinstance(key, (int, Int)) and (_key := int(key)) < 0:
                key = len(self[:]) + _key
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

    @Special._m_repr_
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
                ),
            )
        )
        if len(positional_args) == 1 and len(keyed_args) == 0:
            string += ","

        return String(string)

    def is_positional_only(self) -> bool:
        """Check if the Args contains only positional arguments."""
        # TODO: Use different logic
        from .primitive import Int
        return all(isinstance(k, Int) for k in self._m_dict_)

    def is_keyed_only(self) -> bool:
        """Check if the Args contains only keyed arguments."""
        return len(self) == len(self.keyed_dict())

    def is_mixed_positional_keyed(self) -> bool:
        """Check if the Args contains both positional and keyed arguments."""
        return not self.is_positional_only() and not self.is_keyed_only()

    @classmethod
    def from_positional_keyed(
        cls, positional: Iterable, keyed: dict[Any, Any], /
    ) -> "Args":
        return Args.from_dict(dict(enumerate(positional)) | keyed)

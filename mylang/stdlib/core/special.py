"""Unique symbols."""

from typing import TYPE_CHECKING, final

from ._utils import (
    function_defined_as_class,
    FunctionAsClass,
    python_obj_to_mylang,
    require_parent_locals,
    expose,
    expose_instance_attr,
    str_,
    repr_,
    require_parent_lexical_scope,
)
from .base import Object


if TYPE_CHECKING:
    from ._utils.types import AnyObject


@expose
@expose_instance_attr("name")
@function_defined_as_class()
class Symbol(Object, FunctionAsClass):
    """A unique symbol with a name."""

    _CLASSCALL_SHOULD_RECEIVE_NEW_STACK_FRAME = False

    def __init__(self, name: Object):
        self.name = name

    @classmethod
    def _m_classcall_(cls, args, /):
        """Invoked when the class is called with the given Args."""
        assert len(args) == 1, f"Symbol takes exactly one argument ({len(args)} given)"
        obj = super().__new__(cls)
        obj.__init__(args[0])
        return obj


@expose
@python_obj_to_mylang
def symbol(name: Object) -> Symbol:
    """Create a new symbol with the given name and assign it in the caller's context."""
    sym = Symbol(name)

    require_parent_locals()[name] = sym

    return sym


@expose
@function_defined_as_class()
@final
class Ref(Object, FunctionAsClass):
    _CLASSCALL_SHOULD_RECEIVE_NEW_STACK_FRAME = False

    def __init__(self, obj: "AnyObject"):
        # FIXME: For some reason `ref 1` doesn't throw, even though I didn't
        # explicitly assign set 1=...

        if isinstance(obj, Ref):
            obj = obj.obj

        self.obj: "AnyObject" = obj

    @classmethod
    def to(cls, obj: "AnyObject"):
        """Creates an instance, like `Ref(obj)` would, but for internal use.

        Exists to be used by `call` method, to prevent a recursion, because `Ref`
        is a mylang callable.
        """
        self = super().__new__(cls)
        self.__init__(obj)
        return self

    @classmethod
    def lookup(cls, key: "AnyObject") -> "AnyObject":
        """Get a Ref to the object under `key` in lexical scope."""
        return Ref(require_parent_lexical_scope()[key])

    @classmethod
    def _m_classcall_(cls, args, /):
        self = super().__new__(cls)
        key = args[0]
        self.__init__(key)
        return self

    def __str__(self):
        return f"{self.__class__.__name__}({self.obj})"

    def __repr__(self):
        return f"{self.__class__.__name__}({repr(self.obj)})"

    def _m_str_(self):
        return str_(self.obj)

    def _m_repr_(self):
        return repr_(self.obj)

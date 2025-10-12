"""Unique symbols."""

from ._utils import function_defined_as_class, FunctionAsClass, python_obj_to_mylang, require_parent_locals, expose, expose_instance_attr
from .base import Object


@expose
@expose_instance_attr("name")
@function_defined_as_class
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
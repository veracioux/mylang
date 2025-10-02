from ..core import undefined
from ..core.base import Args, Object
from ..core._utils import expose, function_defined_as_class, FunctionAsClass

__all__ = ("echo",)


# TODO: This is just a crude prototype
@expose
@function_defined_as_class
class echo(Object, FunctionAsClass):
    """Echoes the input value to stdout."""

    _CLASSCALL_SHOULD_RECEIVE_NEW_STACK_FRAME = False

    @classmethod
    def _m_classcall_(cls, args: Args, /):
        """Prints the input value to stdout."""
        print(*(str(arg._m_str_() if hasattr(arg, "_m_str_") else str(arg)) for arg in args[:]))
        return undefined

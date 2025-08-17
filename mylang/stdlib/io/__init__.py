
from mylang.stdlib.core._utils import expose, function_defined_as_class
from ..core.base import Args, Object
from ..core._utils import expose, function_defined_as_class


__all__ = ("echo",)


# TODO: This is just a crude prototype
@expose
@function_defined_as_class
class echo(Object):
    """Echoes the input value to stdout."""

    @classmethod
    def _m_call_(cls, args: Args, /):
        """Prints the input value to stdout."""
        print(*(str(arg) for arg in args[:]))

"""Input/Output functions for mylang.

This module provides basic I/O operations like printing to stdout.
"""

from ..core import undefined
from ..core.base import Args, Object
from ..core._utils import expose, function_defined_as_class, FunctionAsClass, str_


# TODO: This is just a crude prototype
@expose
@function_defined_as_class
class echo(Object, FunctionAsClass):
    """Echoes the input value to stdout."""

    _CLASSCALL_SHOULD_RECEIVE_NEW_STACK_FRAME = False

    @classmethod
    def _m_classcall_(cls, args: Args, /):
        """Prints the input value to stdout."""
        print(*(str_(arg).value for arg in args[:]))
        return undefined

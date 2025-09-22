import sys
import subprocess
from ..core._utils import FunctionAsClass, expose_obj_attr, function_defined_as_class
from ..core import Object, String


@function_defined_as_class
class run(Object, FunctionAsClass):
    _CLASSCALL_SHOULD_RECEIVE_NEW_STACK_FRAME = False

    @classmethod
    def _m_classcall_(cls, args):
        assert args.is_positional_only(), "Only positional arguments are allowed"
        argv = args[:]
        assert all(
            isinstance(arg, String) for arg in argv
        ), "All arguments must be strings"
        subprocess.run(tuple(str(arg) for arg in argv), check=True)


expose_obj_attr(sys.modules[__name__], "run")

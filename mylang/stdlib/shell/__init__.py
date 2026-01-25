import sys

from ..core import undefined, get, fun, Array
from ..core._utils import python_obj_to_mylang, expose_module_attr, require_parent_locals
from ..core._context import internal_module_bridge, current_stack_frame
from ..repl import REPL


_activated = False


mylang = internal_module_bridge.get()


# TODO: Replace with call to the module itself instead
@python_obj_to_mylang
def activate():
    global _activated
    parent_stack_frame = current_stack_frame.get().parent
    assert parent_stack_frame is not None

    require_parent_locals()["get"] = mylang["get"]
    mylang.locals["_py_args"] = Array.from_iterable(sys.argv)
    _activated = True
    return undefined


@python_obj_to_mylang
def run():
    global _activated
    if not _activated:
        activate()
        _activated = True
    return REPL().run()


expose_module_attr("activate", "run")

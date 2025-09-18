from types import ModuleType
from typing import Any

from ..base import Object
from weakref import WeakKeyDictionary


_wrapped_modules: WeakKeyDictionary["PythonModuleWrapper", ModuleType] = (
    WeakKeyDictionary()
)


class PythonModuleWrapper(Object):
    """Wraps a Python module to expose it to MyLang."""

    def __init__(self, module: ModuleType):
        self.module = module
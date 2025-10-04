from types import ModuleType
from ..base import Object


class PythonModuleWrapper(Object):
    """Wraps a Python module to expose it to MyLang."""

    def __init__(self, module: ModuleType):
        self.module = module

    def _m_repr_(self):
        from ..complex import String
        # FIXME
        return String(f'<internal module {self.module.__name__}>')

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


class PythonContext:
    """Holds some privileged Python context for use by MyLang stdlib modules."""
    __slots__ = ("python_module")

    def __init__(self, python_module: ModuleType | None = None):
        self.python_module = python_module
        """The corresponding Python module of the current module being loaded."""

    def __getattr__(self, name):
        return getattr(self.python_module, name)

    def __setattr__(self, name, value):
        if name == "python_module":
            super().__setattr__(name, value)
        else:
            setattr(self.python_module, name, value)

    def __delattr__(self, name):
        delattr(self.python_module, name)
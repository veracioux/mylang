from typing import Any, TYPE_CHECKING, Optional


if TYPE_CHECKING:
    from ..base import Args, String, AnyObject


class ObjectContract:
    _m_name_: Optional[str]
    """Name of the object, if a name other than __name__ is desired."""
    _m_dict_: dict["AnyObject", "AnyObject"]
    """Dictionary of the object's attributes."""
    _m_array_: list["AnyObject"]
    """List of the object's items, if it is array-like."""

    ### Signature constraints for Python dunder methods ###

    def __getitem__(self, key: Any, /) -> "AnyObject":
        _ = key
        raise

    ### Special methods ###

    def _m_init_(self, args: "Args", /) -> None:
        """Initialize the object with the given Args."""
        _ = args
        raise

    def _m_repr_(self) -> "String":
        """Return a string representation of the object that will be used in the mylang context."""
        raise

    def _m_str_(self) -> "String":
        """Convert the object to a MyLang String."""
        raise

    def _m_getattr_(self, key: "AnyObject", /) -> "AnyObject":
        """Get an attribute of the object by key."""
        _ = key
        raise

    def _m_setattr_(self, key: "AnyObject", value: "AnyObject", /) -> None:
        """Set an attribute of the object by key."""
        _ = key, value
        raise

    @classmethod
    def _m_classcall_(cls, args: "Args", /) -> "AnyObject":
        """Invoked when the class is called with the given Args."""
        _ = cls, args
        raise

    def _m_call_(self, args: "Args", /) -> "AnyObject":
        """Invoked when an instance of the class is called with the given Args."""
        _ = self, args
        raise


# These methods are defined in Object:
# 1. so one can inspect their docstrings from implementors.
# 2. to constrain their signatures in subclasses.
# But they should not exist by default unless defined by subclasses.
del ObjectContract._m_repr_
del ObjectContract._m_str_
del ObjectContract._m_getattr_
del ObjectContract._m_setattr_
del ObjectContract._m_classcall_
del ObjectContract._m_call_
del ObjectContract.__getitem__

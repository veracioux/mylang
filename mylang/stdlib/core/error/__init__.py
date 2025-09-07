import dataclasses
from typing import Optional

from .._utils import FunctionAsClass, Special, expose, function_defined_as_class
from ..base import Object
from ..complex import String


@expose
class Error(Object, Exception):
    def __init__(self, message: Optional[str] = None, /):
        self.message: Optional[String]
        super().__init__(message)

    def _m_init_(self, args, /):
        assert len(args) <= 1, "Error takes at most one argument"
        self.message = args[0] if len(args) > 0 else None

    @Special._m_str_
    def _m_str_(self):
        return String(self.message or "")


@dataclasses.dataclass
class ErrorCarrier(Exception):
    """An exception that carries a MyLang error object.

    This is used to allow MyLang errors created in MyLang to be thrown using
    Python's raise.
    """
    error: Error


@expose
@function_defined_as_class
class error(Object, FunctionAsClass):
    """Convenience function to create a custom error"""

    _CLASSCALL_SHOULD_RECEIVE_NEW_STACK_FRAME = False

    @classmethod
    def _create(
        cls, key: String, message: Optional[String] = None, /, base: type[Error] = Error
    ):
        from ..class_ import class_
        from ..func import StatementList, ref

        Err = class_(key, ref.of(base), StatementList())
        def _m_str_(*args):
            return String(message or "") if args else key
        setattr(Err, Special._m_str_.name, _m_str_)
        Err.__name__ = key.value

        return Err

    @classmethod
    @Special._m_classcall_
    def _m_classcall_(cls, args, /):
        positional = args[:]
        key = positional[0]
        assert isinstance(key, String), "error key must be a String"
        message = positional[1] if len(positional) > 1 else None
        assert message is None or isinstance(
            message, String
        ), "message must be a String"
        base = args.keyed_dict().get(String("base"), Error)
        obj = cls._create(
            key, message.value if message is not None else None, base=base
        )

        cls._caller_stack_frame().locals[key] = obj

        return obj

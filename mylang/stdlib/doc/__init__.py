from ..core import Object, String, Args, get
from ..core._utils import FunctionAsClass, expose, repr_, str_


@expose
class RichText(Object):
    content: list[Object]


@expose
class Doc(Object):
    content: RichText


@expose
class SimpleStringDoc(Doc):
    def __init__(self, value: str):
        self.value = value

    def _m_str_(self):
        return String(self.value)

    def _m_repr_(self):
        return repr_(str_(self))


@expose
class doc(Object, FunctionAsClass):
    _CLASSCALL_SHOULD_RECEIVE_NEW_STACK_FRAME = False

    @classmethod
    def _m_classcall_(cls, args: Args, /) -> Doc:
        target_key = args[0]
        target: Object = get(target_key)
        # TODO: Check if there is _m_doc_ metadata on the object
        return SimpleStringDoc(target.__doc__ or getattr(target, "_m_name_", None) or getattr(target, "__name__", ""))

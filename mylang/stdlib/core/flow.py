from ._utils import Special, expose, function_defined_as_class, FunctionAsClass
from .base import class_, Object, Args
from .primitive import undefined


@expose
@function_defined_as_class
class if_(Object, FunctionAsClass):
    _m_name_ = Special._m_name_("if")
    _SHOULD_RECEIVE_NEW_STACK_FRAME = False

    @classmethod
    @Special._m_classcall_
    def _m_classcall_(cls, args, /):
        pass


@expose
@function_defined_as_class
class return_(Object, FunctionAsClass):
    _m_name_ = Special._m_name_("return")
    _SHOULD_RECEIVE_NEW_STACK_FRAME = False

    @classmethod
    @Special._m_classcall_
    def _m_classcall_(cls, args: Args, /):
        # TODO: Make sure return skips execution of remaining statements
        # TODO: Also check that args are positional
        if len(args) > 1:
            raise ValueError("return requires zero or one argument")
        cls._caller_stack_frame().return_value = return_value = (
            args[0] if len(args) == 1 else undefined
        )
        return return_value


# TODO


class Event(class_):
    pass


class react(Object):
    """React to an event."""

    pass

from ._context import current_stack_frame, parent_stack_frame
from .func import StatementList
from ._utils import Special, expose, function_defined_as_class, FunctionAsClass
from .base import class_, Object, Args
from .primitive import undefined


class _Symbols:
    OBJECT_RETURNED_BY_LAST_IF_OR_ELIF = type("OBJECT_RETURNED_BY_LAST_IF_OR_ELIF", (object,), {})()


@expose
@function_defined_as_class
class if_(Object, FunctionAsClass):
    _m_name_ = Special._m_name_("if")
    _SHOULD_RECEIVE_NEW_STACK_FRAME = False

    @classmethod
    @Special._m_classcall_
    def _m_classcall_(cls, args, /):
        # TODO: Validate args
        assert len(args) == 2, "if requires exactly two arguments"
        condition = args[0]
        statement_list = args[1]
        assert isinstance(statement_list, StatementList), (
            "The second argument must be a StatementList"
        )
        if condition:
            value = statement_list.execute()
            current_stack_frame.get().lexical_scope.custom_data[_Symbols.OBJECT_RETURNED_BY_LAST_IF_OR_ELIF] = value
            return value
        else:
            return undefined


@expose
@function_defined_as_class
class else_(Object, FunctionAsClass):
    _m_name_ = Special._m_name_("else")
    _SHOULD_RECEIVE_NEW_STACK_FRAME = False

    @classmethod
    @Special._m_classcall_
    def _m_classcall_(cls, args, /):
        stack_frame = current_stack_frame.get()
        assert stack_frame.lexical_scope.last_called_function is if_, (
            "The else statement must follow an if statement"
        )

        assert len(args) == 1, "else requires exactly one argument"

        statement_list = args[0]

        assert isinstance(statement_list, StatementList), (
            "The argument must be a single StatementList"
        )

        object_returned_by_last_if_elif = stack_frame.lexical_scope.custom_data.get(_Symbols.OBJECT_RETURNED_BY_LAST_IF_OR_ELIF, None)

        if object_returned_by_last_if_elif is None:
            return statement_list.execute()
        else:
            return object_returned_by_last_if_elif

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

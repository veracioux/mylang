from ._context import current_context
from .func import StatementList
from ._utils import expose, function_defined_as_class, FunctionAsClass
from .base import class_, Object, Args
from .primitive import undefined

@expose
@function_defined_as_class
class if_(Object, FunctionAsClass):
    _m_name_ = "if"

    def _m_classcall_(self, args, /):
        # TODO: Validate args
        condition = args[0]
        statement_list = args[1]
        assert isinstance(statement_list, StatementList), "The second argument must be a StatementList"
        if condition:
            return statement_list.execute()
        else:
            return undefined

    @classmethod
    def _m_should_create_nested_context_(cls):
        return False


@expose
@function_defined_as_class
class return_(Object, FunctionAsClass):
    _m_name_ = "return"

    def _m_classcall_(cls, args: Args, /):
        # TODO: Make sure return skips execution of remaining statements
        if len(args) != 1:
            raise ValueError("return requires exactly one argument")
        context = current_context.get()
        context.return_value = args[0]
        return context.get_return_value()

    @classmethod
    def _m_should_create_nested_context_(cls):
        return False


# TODO

class Event(class_):
    pass


class react(Object):
    """React to an event."""
    pass
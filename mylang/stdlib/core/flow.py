from typing import NamedTuple

from .func import StatementList
from ._utils import Special, expose, function_defined_as_class, FunctionAsClass
from ._context import current_stack_frame
from .base import class_, Object, Args
from .primitive import undefined
from .complex import String


class _Symbols:
    CURRENT_IF_BLOCK_DATA = type("_CURRENT_IF_BLOCK_DATA", (object,), {})


@expose
@function_defined_as_class
class if_(Object, FunctionAsClass):
    _m_name_ = Special._m_name_("if")
    _SHOULD_RECEIVE_NEW_STACK_FRAME = False

    class __IfBlockData(NamedTuple):
        modified_statement_list: StatementList

    @classmethod
    @Special._m_classcall_
    def _m_classcall_(cls, args, /):
        from .func import ref

        # TODO: Validate args
        assert len(args) in (1, 2), "if requires 1 or 2 arguments"
        condition = args[0] if len(args) == 2 else None
        statement_list = args[-1]
        assert isinstance(
            statement_list, StatementList
        ), "The last argument must be a StatementList"
        # Complex if statement with nested conditions and (optional) else
        if condition is None:
            # TODO: Make this kind of behavior a first-class citizen
            stud_args = Args(None)
            modified_statement_list = StatementList.from_iterable(
                (stud_args + Args(statement)) for statement in statement_list
            )
            for i, orig_statement in enumerate(statement_list):
                orig_statement: Args
                assert isinstance(
                    orig_statement[-1], StatementList
                ), "The last argument in each statement of an if-else block must be a StatementList"
                if isinstance(orig_statement[0], String) and orig_statement[
                    0
                ] == String("else"):
                    from .func import call

                    assert len(orig_statement) == 2, "else must have exactly 1 argument"
                    assert (
                        i == len(statement_list) - 1
                    ), "else must be the last statement in an if-else block"
                    modified_statement_list[i][0] = ref.of(call)
                    modified_statement_list[i][1] = ref.of(cls.__Else)
                else:
                    assert (
                        orig_statement.is_positional_only() and len(orig_statement) == 2
                    ), "condition statement must have exactly 2 arguments"
                    # Replace the first argument with a ref of `if` (the simple case with a single condition)
                    modified_statement_list[i][0] = ref.of(cls)

            current_stack_frame.get().lexical_scope.custom_data[
                _Symbols.CURRENT_IF_BLOCK_DATA
            ] = cls.__IfBlockData(modified_statement_list)

            value = modified_statement_list.execute()
            return value
        # Simple if statement with single condition
        elif condition:
            if_block_data = current_stack_frame.get().lexical_scope.custom_data.get(
                _Symbols.CURRENT_IF_BLOCK_DATA, None
            )
            if if_block_data is not None:
                if_block_data.modified_statement_list.aborted = True
            return statement_list.execute()
        else:
            return undefined

    @function_defined_as_class
    class __Else(FunctionAsClass):
        _SHOULD_RECEIVE_NEW_STACK_FRAME = False

        @classmethod
        @Special._m_classcall_
        def _m_classcall_(cls, args: Args, /):
            assert len(args) == 1, "if requires exactly 1 argument"
            assert isinstance(
                statement_list := args[0], StatementList
            ), "if requires exactly 1 argument"
            return statement_list.execute()

    @classmethod
    def _update_if_block_data(
        cls,
    ):
        """Update the data regarding the current if-else block in the current stack frame."""
        current_stack_frame.get().lexical_scope.custom_data.setdefault(
            _Symbols.CURRENT_IF_BLOCK_DATA, cls.__IfBlockData()
        )


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


# TODO: Maybe move somewhere else
@expose
@function_defined_as_class
class ignore(Object, FunctionAsClass):
    """Do nothing. Ignores all its arguments."""

    _SHOULD_RECEIVE_NEW_STACK_FRAME = False

    @classmethod
    @Special._m_classcall_
    def _m_classcall_(cls, args: Args, /):
        return undefined


# TODO


class Event(class_):
    pass


class react(Object):
    """React to an event."""

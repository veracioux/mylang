import abc
import dataclasses
from typing import NamedTuple

from .func import StatementList
from ._utils import expose, function_defined_as_class, FunctionAsClass, issubclass_
from .base import Object, Args
from .primitive import undefined
from .complex import String
from .error import Error, ErrorCarrier
from ._context import CatchSpec


class _Symbols:
    CURRENT_IF_BLOCK_DATA = type("_CURRENT_IF_BLOCK_DATA", (object,), {})
    CURRENT_LOOP_DATA = type("_CURRENT_LOOP_DATA", (object,), {})


@dataclasses.dataclass
class _LoopData:
    copied_statement_list: StatementList
    broken: bool = False
    should_continue: bool = False


@expose
@function_defined_as_class
class if_(Object, FunctionAsClass):
    _m_name_ = "if"
    _CLASSCALL_SHOULD_RECEIVE_NEW_STACK_FRAME = False

    class __IfBlockData(NamedTuple):
        modified_statement_list: StatementList

    @classmethod
    def _m_classcall_(cls, args, /):
        from .func import ref

        # TODO: Validate args
        assert len(args) in (1, 2), "if requires 1 or 2 arguments"
        condition = args[0] if len(args) == 2 else None
        statement_list = args[-1]
        assert isinstance(
            statement_list, StatementList
        ), "The last argument of an if must be a StatementList"
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

            cls._caller_stack_frame().lexical_scope.custom_data[
                _Symbols.CURRENT_IF_BLOCK_DATA
            ] = cls.__IfBlockData(modified_statement_list)

            value = modified_statement_list.execute()
            return value
        # Simple if statement with single condition
        elif condition:
            if_block_data = cls._caller_stack_frame().lexical_scope.custom_data.get(
                _Symbols.CURRENT_IF_BLOCK_DATA, None
            )
            if if_block_data is not None:
                if_block_data.modified_statement_list.aborted = True
            return statement_list.execute()
        else:
            return undefined

    @function_defined_as_class
    class __Else(FunctionAsClass):
        _CLASSCALL_SHOULD_RECEIVE_NEW_STACK_FRAME = False

        @classmethod
        def _m_classcall_(cls, args: Args, /):
            assert len(args) == 1, "if requires exactly 1 argument"
            assert isinstance(
                statement_list := args[0], StatementList
            ), "if requires exactly 1 argument"
            return statement_list.execute()


@expose
@function_defined_as_class
class return_(Object, FunctionAsClass):
    _m_name_ = "return"
    _CLASSCALL_SHOULD_RECEIVE_NEW_STACK_FRAME = False

    @classmethod
    def _m_classcall_(cls, args: Args, /):
        # TODO: Make sure return skips execution of remaining statements
        # TODO: Also check that args are positional
        if len(args) > 1:
            raise ValueError("return requires zero or one argument")
        cls._caller_stack_frame().return_value = return_value = (
            args[0] if len(args) == 1 else undefined
        )
        return return_value


@expose
@function_defined_as_class
class loop(Object, FunctionAsClass):
    """Loop forever, until a `break` statement is encountered, or a `while`
    condition is no longer true."""

    _CLASSCALL_SHOULD_RECEIVE_NEW_STACK_FRAME = False

    @classmethod
    def _m_classcall_(cls, args: Args, /):
        assert len(args) == 1, "loop requires exactly one argument"
        assert isinstance(
            args[0], StatementList
        ), "The argument to loop must be a StatementList"

        copied_statement_list = StatementList.from_iterable(args[0])
        stack_frame = cls._caller_stack_frame()
        loop_data = _LoopData(copied_statement_list=copied_statement_list)
        cls._caller_lexical_scope().custom_data[_Symbols.CURRENT_LOOP_DATA] = loop_data
        # TODO: Consider adding some return value from the loop
        while True:
            # Execute statement list (it will abort something breaks or continues the loop)
            copied_statement_list.execute()

            # Check if break or return was called
            if loop_data.broken or stack_frame.return_value is not None:
                return undefined
            # Check if continue was called
            elif loop_data.should_continue:
                loop_data.should_continue = False
                copied_statement_list.aborted = False


@expose
@function_defined_as_class
class for_(Object, FunctionAsClass):
    _m_name_ = "for"
    _CLASSCALL_SHOULD_RECEIVE_NEW_STACK_FRAME = True

    @classmethod
    def _m_classcall_(cls, args: Args, /):
        from ._context import current_stack_frame
        from ._utils import iter_
        assert args.is_positional_only() and len(args) == 4, "for requires exactly 4 positional arguments"
        loop_var, in_, iterable, statement_list = args[:]
        assert in_ == String("in"), "The second argument to for must be 'in'"
        assert isinstance(statement_list, StatementList), "The last argument to for must be a StatementList"

        stack_frame = current_stack_frame.get()
        stack_frame.set_parent_lexical_scope(stack_frame.parent.lexical_scope)
        for value in iter_(iterable):
            stack_frame.locals[loop_var] = value
            statement_list.execute()

        return undefined


class _LoopControlFunction(Object, FunctionAsClass, abc.ABC):
    """Base class for loop control functions like while, break, etc."""
    _CLASSCALL_SHOULD_RECEIVE_NEW_STACK_FRAME = False

    @classmethod
    @abc.abstractmethod
    def _m_classcall_(cls, args: Args, /): ...

    @classmethod
    def _get_loop_data(cls) -> _LoopData:
        loop_data = cls._caller_lexical_scope().custom_data.get(
            _Symbols.CURRENT_LOOP_DATA, None
        )
        assert (
            loop_data is not None
        ), f"{cls._m_name_} statement not inside a loop"
        return loop_data


@expose
@function_defined_as_class
class while_(_LoopControlFunction):
    _m_name_ = "while"

    @classmethod
    def _m_classcall_(cls, args: Args, /):
        assert len(args) == 1, "while requires exactly 1 argument"
        condition = args[0]
        loop_data = cls._get_loop_data()

        if not condition:
            loop_data.broken = True
            loop_data.copied_statement_list.aborted = True
            return undefined


@expose
@function_defined_as_class
class break_(_LoopControlFunction):
    """Break out of a loop."""

    _m_name_ = "break"
    _CLASSCALL_SHOULD_RECEIVE_NEW_STACK_FRAME = False

    @classmethod
    def _m_classcall_(cls, args: Args, /):
        if len(args) != 0:
            raise ValueError("break does not take any arguments")
        loop_data = cls._get_loop_data()
        loop_data.broken = True
        loop_data.copied_statement_list.aborted = True
        return undefined


@expose
@function_defined_as_class
class continue_(_LoopControlFunction):
    _m_name_ = "continue"
    _CLASSCALL_SHOULD_RECEIVE_NEW_STACK_FRAME = False

    @classmethod
    def _m_classcall_(cls, args: Args, /):
        if len(args) != 0:
            raise ValueError("continue does not take any arguments")
        loop_data = cls._get_loop_data()
        loop_data.should_continue = True
        loop_data.copied_statement_list.aborted = True
        return undefined


# TODO: Maybe move somewhere else
@expose
@function_defined_as_class
class ignore(Object, FunctionAsClass):
    """Do nothing. Ignores all its arguments."""

    _CLASSCALL_SHOULD_RECEIVE_NEW_STACK_FRAME = False

    @classmethod
    def _m_classcall_(cls, args: Args, /):
        return undefined


@expose
@function_defined_as_class
class try_(Object, FunctionAsClass):
    _m_name_ = "try"

    _CLASSCALL_SHOULD_RECEIVE_NEW_STACK_FRAME = False

    @classmethod
    def _m_classcall_(cls, args: Args, /):
        assert len(args) >= 1 and isinstance(body := args[0], StatementList), "try's first argument must be a StatementList"
        assert len(args) >= 3, "try requires 'catch' and a catch body"
        assert args[1] == String("catch"), "try's 2nd argument must be 'catch'"
        error_key = args[2] if len(args) == 4 else None

        assert isinstance(catch_body := args[-1], StatementList), "catch's body must be a StatementList"
        cls.__validate_catch_body(catch_body)

        cls._caller_stack_frame().catch_spec = CatchSpec(error_key, catch_body)

        return body.execute()

    @classmethod
    def __validate_catch_body(cls, catch_body: StatementList):
        for statement in catch_body:
            assert statement.is_positional_only(), "Each statement in a catch body must be positional-only"
            assert len(statement) >= 2, "Each statement in a catch body must have exactly 2 arguments"
            assert isinstance(statement[-1], StatementList), "The second argument in each statement of a catch body must be a StatementList"


@expose
@function_defined_as_class
class throw(Object, FunctionAsClass):
    _CLASSCALL_SHOULD_RECEIVE_NEW_STACK_FRAME = False

    @classmethod
    def _m_classcall_(cls, args: Args, /):
        if len(args) == 0:
            raise Error()
        else:
            if isinstance(args[0], Error):
                assert (
                    len(args) == 1
                ), "throw does not accept extra arguments after an Error instance"
                raise args[0]
            else:
                from .func import get

                if issubclass_(args[0], Error):
                    error_class = args[0]
                else:
                    error_class = get(args[0])
                error_class: type[Exception]
                remaining_args = Args(*args[1:]) + Args.from_dict(args.keyed_dict())
                error = error_class(remaining_args)
                if isinstance(error, Error):
                    raise error
                else:
                    raise ErrorCarrier(error)
        raise Error(args[0])

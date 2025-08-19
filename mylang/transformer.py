from lark import Transformer as _Transformer, Token, Tree

from mylang.stdlib.core._context import nested_context
from .stdlib.core import (
    Args,
    Bool,
    Dict,
    Float,
    Int,
    Object,
    String,
    null,
    undefined,
    Array,
    call,
    set,
)

__all__ = ("Transformer", "StatementList", "ExecutionBlock")


class StatementList(Array):
    def execute(self) -> Object:
        for i_statement, statement in enumerate(self):
            result: Object
            # Make sure an expression is converted to Args. If already Args, it
            # won't be modified
            args = Args(statement)

            # Iterate through all top-level items (positional args + keys + values)
            # and make sure that if they are an ExecutionBlock, it gets executed.
            for i_posarg, posarg in enumerate(args[:]):
                if isinstance(posarg, ExecutionBlock):
                    args[i_posarg] = posarg.execute()
            for key, value in args.keyed_dict().items():
                if isinstance(key, ExecutionBlock):
                    key = key.execute()

                args[key] = (
                    value.execute()
                    if isinstance(value, ExecutionBlock)
                    else value
                )

            if args.is_keyed_only():
                result = set(args)
            else:
                result = call(args)

            if i_statement == len(self) - 1:
                return result

    def _m_repr_(self):
        return String("{" + type(self).__name__ + " " + str(super()._m_repr_()) + "}")


class ExecutionBlock(StatementList):
    def execute(self) -> Object:
        with nested_context({}):
            return super().execute()


class Transformer(_Transformer):
    def BOOL(self, token: Token):
        return Bool(token.value == "true")

    def SIGNED_NUMBER(self, token: Token):
        pythonic: int | float
        try:
            pythonic = int(token.value)
        except ValueError:
            pythonic = float(token)
        return Int(pythonic) if isinstance(pythonic, int) else Float(pythonic)

    def NULL(self, _):
        return null

    def UNDEFINED(self, _):
        return undefined

    def UNQUOTED_STRING(self, token: Token):
        return String(token.value)

    def ESCAPED_STRING(self, token: Token):
        return String(eval(token.value))  # pylint: disable=eval-used

    def args(self, items: list[Tree | Object]):
        dict_ = {
            # Positional arguments
            index: item
            for index, item in enumerate(items)
            if not isinstance(item, Tree)
        } | {
            # Keyed arguments
            self.transform(item.children[0]): self.transform(item.children[1])
            for item in items
            if isinstance(item, Tree) and item.data == "assignment"
        }

        return Args.from_dict(dict_)

    def dict(self, items: list[Tree | Object]):
        return Dict(self.args(items))

    def array(self, items: list[Object]):
        return Array.from_list(items)

    def statement_list(self, statements: list[Object]):
        return StatementList.from_list(statements)

    def execution_block(self, items: tuple[StatementList]):
        return ExecutionBlock.from_list(items[0])

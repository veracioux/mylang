"""Transformer for converting Lark parse trees to mylang AST objects."""

from lark import Transformer as _Transformer, Token, Tree

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
    BinaryOperation,
    PostfixOperation,
    PrefixOperation,
    Dots,
    Path,
)

from .stdlib.core.func import StatementList, ExecutionBlock


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
        return String(eval(token.value))  # TODO: Replace or thoroughly test

    def SINGLE_QUOTED_STRING(self, token: Token):
        return String(eval(token.value))  # TODO: Replace or thoroughly test

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
        return Array.from_iterable(items)

    def statement_list(self, statements: list[Args]):
        return StatementList.from_iterable(statements)

    def execution_block(self, items: tuple[StatementList]):
        return ExecutionBlock.from_iterable(items[0])

    def execution_block_single_statement(self, items: list[Object | Tree]):
        return StatementList.from_iterable([self.args(items)])

    def prefix_operation(self, items: tuple[Tree, Object]):
        return PrefixOperation(_operator_node_to_string(items[0]), items[1])

    def postfix_operation(self, items: tuple[Object, Tree]):
        return PostfixOperation(_operator_node_to_string(items[1]), items[0])

    def binary_operation(self, items: tuple[Tree, Object, Object]):
        return BinaryOperation(_operator_node_to_string(items[1]), [items[0], items[2]])

    def dots(self, items: list[Token]):
        return Dots(len(items[0].value))

    def path(self, items: list[Object]):
        return Path(Args(*items))

    def module(self, items: tuple[StatementList | Args | Object]):
        if not items:
            return StatementList()
        elif isinstance(items[0], Args):
            return StatementList.from_iterable([items[0]])
        elif isinstance(items[0], StatementList):
            return items[0]
        else:
            return StatementList.from_iterable([Args(items[0])])

    def wrapped_args(self, items: list[Object | Tree]):
        raise NotImplementedError


def _operator_node_to_string(operator: Tree):
    """The parsed operator yields a tree whose children are string tokens. This function merges them."""
    return "".join(operator.children)

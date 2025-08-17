from lark import Transformer as _Transformer, Token, Tree
from mylang.stdlib.core import (
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
)

__all__ = ("Transformer", "StatementList")


class StatementList(Array):
    pass


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

    def statement_list(self, statements: list[Object]):
        return StatementList(*statements)

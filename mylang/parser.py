from lark import Lark
from pathlib import Path


__all__ = ("parser", "EXPRESSION", "STATEMENT_LIST")


EXPRESSION = "expression"
STATEMENT_LIST = "statement_list"

_start = [
    STATEMENT_LIST,
    EXPRESSION,
    "args",
    "assignment",
    "dict",
    "path",
]

with open(Path(__file__).parent.absolute() / "mylang.lark") as f:
    parser = Lark(
        f,
        # parser="lalr",
        start=_start,
    )

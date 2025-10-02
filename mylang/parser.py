"""Parser module for MyLang using Lark."""

from pathlib import Path
from lark import Lark


__all__ = ("parser",)


_start = [
    "module",
    "statement_list",
    "expression",
    "execution_block",
    "args",
    "array",
    "wrapped_args",
    "assignment",
    "dict",
    "path",
]

with open(Path(__file__).parent.absolute() / "mylang.lark", encoding="utf-8") as f:
    parser = Lark(
        f,
        # parser="lalr",
        start=_start,
    )

from lark import Lark
from pathlib import Path


__all__ = ("parser", "EXPRESSION", "STATEMENT_LIST")

with open(Path(__file__).parent.absolute() / "mylang.lark") as f:
    parser = Lark(
        f,
        start=[
            "statement_list",
            "expression",
            "args",
            "assignment",
            "dict",
        ],
    )


EXPRESSION = "expression"
STATEMENT_LIST = "statement_list"

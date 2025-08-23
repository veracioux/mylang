import abc
import dataclasses
from contextlib import contextmanager
import enum
import re
from typing import Any, Generic, TextIO, TypeVar, Union, final
from lark import Lark
from pathlib import Path

from .stdlib.core import String, Object, Args, call, set_, Primitive, Number, Bool, undefined, null, Float, Int
from .stdlib.core._context import nested_stack_frame


__all__ = ("parser", "EXPRESSION", "STATEMENT_LIST")


EXPRESSION = "expression"
STATEMENT_LIST = "statement_list"

_start = [
    STATEMENT_LIST,
    EXPRESSION,
    "args",
    "assignment",
    "dict",
]

with open(Path(__file__).parent.absolute() / "mylang.lark") as f:
    parser = Lark(
        f,
        # parser="lalr",
        start=_start,
    )

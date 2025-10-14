"""Core mylang standard library module.

This module provides the fundamental building blocks of the mylang programming language,
including primitive types, complex types, base classes, functions, control flow constructs,
and error handling.
"""

from .primitive import (
    Primitive,
    Scalar,
    Number,
    Int,
    Float,
    Bool,
    Undefined,
    Null,
    undefined,
    null,
    true,
    false,
)
from .complex import String, Path, Dots
from .base import (
    Object,
    Args,
    Dict,
    Array,
    Operation,
    PrefixOperation,
    PostfixOperation,
    BinaryOperation,
    IncompleteExpression,
    UnaryOperation,
    TypedObject,
)
from .func import fun, call, set_, get, use, ref, op, export, StatementList, ExecutionBlock
from .flow import if_, return_, loop, while_, break_, continue_, throw, try_, for_
from .class_ import class_
from .error import Error, error
from .symbol import Symbol, symbol
from .context import Context, context

__all__ = (
    "Primitive",
    "Scalar",
    "Number",
    "Int",
    "Float",
    "Bool",
    "Undefined",
    "Null",
    "undefined",
    "null",
    "true",
    "false",
    "String",
    "Path",
    "Dots",
    "Object",
    "Args",
    "Dict",
    "Array",
    "Operation",
    "PrefixOperation",
    "PostfixOperation",
    "BinaryOperation",
    "IncompleteExpression",
    "UnaryOperation",
    "TypedObject",
    "fun",
    "call",
    "set_",
    "get",
    "use",
    "ref",
    "export",
    "StatementList",
    "ExecutionBlock",
    "if_",
    "return_",
    "loop",
    "while_",
    "break_",
    "continue_",
    "throw",
    "try_",
    "for_",
    "class_",
    "Error",
    "error",
    "Symbol",
    "symbol",
    "op",
    "context",
    "Context",
)

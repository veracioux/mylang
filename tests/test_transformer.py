# pylint: disable=missing-function-docstring,missing-module-docstring,invalid-name

import pytest
from lark import Token, Tree
from mylang.transformer import Transformer
from mylang.stdlib.core.func import StatementList
from mylang.stdlib.core import (
    Args,
    Array,
    BinaryOperation,
    Bool,
    Dict,
    Dots,
    ExecutionBlock,
    Float,
    Int,
    Path,
    PostfixOperation,
    PrefixOperation,
    String,
    null,
    undefined,
)


class TestTransformer:
    def setup_method(self):
        self.transformer = Transformer()

    def test_BOOL_true(self):
        token = Token("BOOL", "true")
        result = self.transformer.BOOL(token)
        assert isinstance(result, Bool)
        assert result.value is True

    def test_BOOL_false(self):
        token = Token("BOOL", "false")
        result = self.transformer.BOOL(token)
        assert isinstance(result, Bool)
        assert result.value is False

    def test_SIGNED_NUMBER_int(self):
        token = Token("SIGNED_NUMBER", "42")
        result = self.transformer.SIGNED_NUMBER(token)
        assert isinstance(result, Int)
        assert result.value == 42

    def test_SIGNED_NUMBER_negative_int(self):
        token = Token("SIGNED_NUMBER", "-42")
        result = self.transformer.SIGNED_NUMBER(token)
        assert isinstance(result, Int)
        assert result.value == -42

    def test_SIGNED_NUMBER_float(self):
        token = Token("SIGNED_NUMBER", "3.14")
        result = self.transformer.SIGNED_NUMBER(token)
        assert isinstance(result, Float)
        assert result.value == 3.14

    def test_SIGNED_NUMBER_negative_float(self):
        token = Token("SIGNED_NUMBER", "-3.14")
        result = self.transformer.SIGNED_NUMBER(token)
        assert isinstance(result, Float)
        assert result.value == -3.14

    def test_NULL(self):
        result = self.transformer.NULL(None)
        assert result is null

    def test_UNDEFINED(self):
        result = self.transformer.UNDEFINED(None)
        assert result is undefined

    def test_UNQUOTED_STRING(self):
        token = Token("UNQUOTED_STRING", "hello")
        result = self.transformer.UNQUOTED_STRING(token)
        assert isinstance(result, String)
        assert result.value == "hello"

    def test_ESCAPED_STRING_empty(self):
        token = Token("ESCAPED_STRING", '""')
        result = self.transformer.ESCAPED_STRING(token)
        assert isinstance(result, String)
        assert result.value == ""

    def test_ESCAPED_STRING_complex_escapes(self):
        token = Token("ESCAPED_STRING", '"\\n\\t\\r\\f\\b\\\\"')
        result = self.transformer.ESCAPED_STRING(token)
        assert isinstance(result, String)
        assert result.value == "\n\t\r\f\b\\"

    def test_ESCAPED_STRING(self):
        token = Token("ESCAPED_STRING", '"hello world"')
        result = self.transformer.ESCAPED_STRING(token)
        assert isinstance(result, String)
        assert result.value == "hello world"

    def test_ESCAPED_STRING_with_escapes(self):
        token = Token("ESCAPED_STRING", r'"hello\nworld"')
        result = self.transformer.ESCAPED_STRING(token)
        assert isinstance(result, String)
        assert result.value == "hello\nworld"

    def test_SINGLE_QUOTED_STRING_empty(self):
        token = Token("SINGLE_QUOTED_STRING", "''")
        result = self.transformer.SINGLE_QUOTED_STRING(token)
        assert isinstance(result, String)
        assert result.value == ""

    def test_SINGLE_QUOTED_STRING(self):
        token = Token("SINGLE_QUOTED_STRING", r"'hello world'")
        result = self.transformer.SINGLE_QUOTED_STRING(token)
        assert isinstance(result, String)
        assert result.value == "hello world"

    def test_SINGLE_QUOTED_STRING_with_escapes(self):
        token = Token("SINGLE_QUOTED_STRING", r"'hello\nworld'")
        result = self.transformer.SINGLE_QUOTED_STRING(token)
        assert isinstance(result, String)
        assert result.value == "hello\nworld"

    def test_SINGLE_QUOTED_STRING_with_tab_escape(self):
        token = Token("SINGLE_QUOTED_STRING", r"'hello\tworld'")
        result = self.transformer.SINGLE_QUOTED_STRING(token)
        assert isinstance(result, String)
        assert result.value == "hello\tworld"

    def test_SINGLE_QUOTED_STRING_with_backslash_escape(self):
        token = Token("SINGLE_QUOTED_STRING", r"'path\to\file'")
        result = self.transformer.SINGLE_QUOTED_STRING(token)
        assert isinstance(result, String)
        assert result.value == "path\to\file"

    def test_SINGLE_QUOTED_STRING_unicode_escape(self):
        token = Token("SINGLE_QUOTED_STRING", r"'\u0041'")
        result = self.transformer.SINGLE_QUOTED_STRING(token)
        assert isinstance(result, String)
        assert result.value == "A"

    def test_SINGLE_QUOTED_STRING_with_single_quote_escape(self):
        token = Token("SINGLE_QUOTED_STRING", r"'It\'s working'")
        result = self.transformer.SINGLE_QUOTED_STRING(token)
        assert isinstance(result, String)
        assert result.value == "It's working"

    def test_SINGLE_QUOTED_STRING_with_double_quote_unescaped(self):
        token = Token("SINGLE_QUOTED_STRING", "'He said \"hello\" to me'")
        result = self.transformer.SINGLE_QUOTED_STRING(token)
        assert isinstance(result, String)
        assert result.value == 'He said "hello" to me'

    def test_args_positional_only(self):
        items = [String("a"), Int(1), Float(2.5)]
        result = self.transformer.args(items)
        assert isinstance(result, Args)
        # Check positional arguments are properly indexed
        assert result[Int(0)] == String("a")
        assert result[Int(1)] == Int(1)
        assert result[Int(2)] == Float(2.5)

    def test_args_keyed_only(self):
        assignment_tree = Tree("assignment", [String("key"), Int(42)])
        items = [assignment_tree]

        result = self.transformer.args(items)
        assert isinstance(result, Args)
        assert result[String("key")] == Int(42)

    def test_args_mixed_positional_and_keyed(self):
        assignment_tree = Tree("assignment", [String("key"), Int(42)])
        items = [String("positional"), assignment_tree]

        result = self.transformer.args(items)
        assert isinstance(result, Args)
        assert result[Int(0)] == String("positional")
        assert result[String("key")] == Int(42)

    def test_args_empty(self):
        items = []
        result = self.transformer.args(items)
        assert isinstance(result, Args)

    def test_dict(self):
        items = [String("value")]
        result = self.transformer.dict(items)
        assert isinstance(result, Dict)
        assert result._m_dict_ == {Int(0): String("value")}

    def test_statement_list(self):
        statements = [String("a"), Int(1), Bool(True)]
        result = self.transformer.statement_list(statements)
        assert isinstance(result, StatementList)
        assert len(result) == 3
        assert result[0] == String("a")
        assert result[1] == Int(1)
        assert result[2] == Bool(True)

    def test_statement_list_empty(self):
        statements = []
        result = self.transformer.statement_list(statements)
        assert isinstance(result, StatementList)
        assert len(result) == 0

    def test_statement_list_single_call(self):
        statements = [Args("set", a=1)]
        result = self.transformer.statement_list(statements)
        assert isinstance(result, StatementList)
        assert result == [Args("set", a=1)]

    def test_array(self):
        items = [String("a"), Int(1), Float(2.5)]
        result = self.transformer.array(items)
        assert isinstance(result, Array)
        assert len(result) == 3
        assert result[0] == String("a")
        assert result[1] == Int(1)
        assert result[2] == Float(2.5)

    def test_array_empty(self):
        items = []
        result = self.transformer.array(items)
        assert isinstance(result, Array)
        assert len(result) == 0

    def test_execution_block(self):
        statement_list = StatementList.from_iterable([Args("echo", String("hello"))])
        items = (statement_list,)
        result = self.transformer.execution_block(items)
        assert isinstance(result, ExecutionBlock)
        assert len(result) == 1
        assert result[0] == Args("echo", String("hello"))

    def test_execution_block_single_statement(self):
        items = [String("echo"), String("hello")]
        result = self.transformer.execution_block_single_statement(items)
        assert isinstance(result, StatementList)
        assert len(result) == 1
        assert isinstance(result[0], Args)

    def test_prefix_operation(self):
        operator_tree = Tree("operator", [Token("OPERATOR", "-")])
        operand = Int(42)
        items = (operator_tree, operand)
        result = self.transformer.prefix_operation(items)
        assert isinstance(result, PrefixOperation)
        assert result.operator == "-"
        assert result.operand == Int(42)

    def test_postfix_operation(self):
        operand = Int(42)
        operator_tree = Tree("operator", [Token("OPERATOR", "!")])
        items = (operand, operator_tree)
        result = self.transformer.postfix_operation(items)
        assert isinstance(result, PostfixOperation)
        assert result.operator == "!"
        assert result.operand == Int(42)

    def test_binary_operation(self):
        left_operand = Int(10)
        operator_tree = Tree("operator", [Token("OPERATOR", "+")])
        right_operand = Int(5)
        items = (left_operand, operator_tree, right_operand)
        result = self.transformer.binary_operation(items)
        assert isinstance(result, BinaryOperation)
        assert result.operator == "+"
        assert result.operands == [Int(10), Int(5)]

    def test_dots(self):
        token = Token("DOTS", "...")
        items = [token]
        result = self.transformer.dots(items)
        assert isinstance(result, Dots)
        assert result.count == 3

    def test_dots_single(self):
        token = Token("DOTS", ".")
        items = [token]
        result = self.transformer.dots(items)
        assert isinstance(result, Dots)
        assert result.count == 1

    def test_path(self):
        items = [String("a"), String("b"), String("c")]
        result = self.transformer.path(items)
        assert isinstance(result, Path)
        assert len(result.parts) == 3

    def test_module_with_args(self):
        args = Args("echo", String("hello"))
        items = (args,)
        result = self.transformer.module(items)
        assert isinstance(result, StatementList)
        assert len(result) == 1
        assert result[0] == args

    def test_module_with_statement_list(self):
        statement_list = StatementList.from_iterable([Args("echo", String("hello"))])
        items = (statement_list,)
        result = self.transformer.module(items)
        assert result == statement_list

    def test_module_with_object(self):
        obj = String("hello")
        items = (obj,)
        result = self.transformer.module(items)
        assert isinstance(result, StatementList)
        assert len(result) == 1
        assert isinstance(result[0], Args)

    def test_wrapped_args(self):
        items = [String("test")]
        with pytest.raises(NotImplementedError):
            self.transformer.wrapped_args(items)

    def test_SIGNED_NUMBER_zero(self):
        token = Token("SIGNED_NUMBER", "0")
        result = self.transformer.SIGNED_NUMBER(token)
        assert isinstance(result, Int)
        assert result.value == 0

    def test_SIGNED_NUMBER_zero_float(self):
        token = Token("SIGNED_NUMBER", "0.0")
        result = self.transformer.SIGNED_NUMBER(token)
        assert isinstance(result, Float)
        assert result.value == 0.0

    def test_SIGNED_NUMBER_large_int(self):
        token = Token("SIGNED_NUMBER", "123456789012345678901234567890")
        result = self.transformer.SIGNED_NUMBER(token)
        assert isinstance(result, Int)
        assert result.value == 123456789012345678901234567890

    def test_SIGNED_NUMBER_scientific_float(self):
        token = Token("SIGNED_NUMBER", "1.23e-4")
        result = self.transformer.SIGNED_NUMBER(token)
        assert isinstance(result, Float)
        assert result.value == 1.23e-4
from lark import Token, Tree
from mylang.transformer import Transformer, StatementList
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

    def test_ESCAPED_STRING(self):
        token = Token("ESCAPED_STRING", '"hello world"')
        result = self.transformer.ESCAPED_STRING(token)
        assert isinstance(result, String)
        assert result.value == "hello world"

    def test_ESCAPED_STRING_with_escapes(self):
        token = Token("ESCAPED_STRING", '"hello\\nworld"')
        result = self.transformer.ESCAPED_STRING(token)
        assert isinstance(result, String)
        assert result.value == "hello\nworld"

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

        # Mock the transform method to return the expected values
        self.transformer.transform = lambda x: x

        result = self.transformer.args(items)
        assert isinstance(result, Args)
        assert result[String("key")] == Int(42)

    def test_args_mixed_positional_and_keyed(self):
        assignment_tree = Tree("assignment", [String("key"), Int(42)])
        items = [String("positional"), assignment_tree]

        # Mock the transform method to return the expected values
        self.transformer.transform = lambda x: x

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
        assert result == [
            Args("set", a=1)
        ]

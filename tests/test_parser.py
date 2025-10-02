# pylint: disable=missing-function-docstring,missing-module-docstring

import pytest
from lark import Tree, UnexpectedCharacters, UnexpectedEOF
from mylang.parser import parser

_Tree_repr = Tree.__repr__


def Tree_repr(self: "Tree"):  # pylint: disable=invalid-name
    print(self.pretty())
    return _Tree_repr(self)


Tree.__repr__ = Tree_repr


class TestPrimitive:
    def test_parse_bool(self):
        t = parser.parse("true", start="expression")
        assert t.type == "BOOL"
        assert t.value == "true"

        t = parser.parse("false", start="expression")
        assert t.type == "BOOL"
        assert t.value == "false"

    def test_parse_int(self):
        t = parser.parse("0", start="expression")
        assert t.type == "SIGNED_NUMBER"
        assert t.value == "0"

        t = parser.parse("123", start="expression")
        assert t.type == "SIGNED_NUMBER"
        assert t.value == "123"

        t = parser.parse("-123", start="expression")

    def test_parse_float(self):
        t = parser.parse("0.0", start="expression")
        assert t.type == "SIGNED_NUMBER"
        assert t.value == "0.0"

        t = parser.parse("123.456", start="expression")
        assert t.type == "SIGNED_NUMBER"
        assert t.value == "123.456"

        t = parser.parse("+123.456", start="expression")
        assert t.type == "SIGNED_NUMBER"
        assert t.value == "+123.456"

        t = parser.parse("-123.456", start="expression")
        assert t.type == "SIGNED_NUMBER"
        assert t.value == "-123.456"

        t = parser.parse("1.", start="expression")
        assert t.type == "SIGNED_NUMBER"
        assert t.value == "1."

        t = parser.parse("-1.", start="expression")
        assert t.type == "SIGNED_NUMBER"
        assert t.value == "-1."

        t = parser.parse(".1", start="expression")
        assert t.type == "SIGNED_NUMBER"
        assert t.value == ".1"

        t = parser.parse("-.1", start="expression")
        assert t.type == "SIGNED_NUMBER"
        assert t.value == "-.1"


class TestAssignment:
    def test_parse_assignment(self):
        t = parser.parse("a=1", start="assignment")
        assert (
            t.pretty().strip()
            == """
assignment
  a
  1
""".strip()
        )

    def test_parse_assignment_spaced(self):
        t = parser.parse('"a" = 1', start="assignment")
        assert (
            t.pretty().strip()
            == """
assignment
  "a"
  1
""".strip()
        )

    def test_parse_assignment_complex_lvalue(self):
        t = parser.parse("{a=1 b=2} = 1", start="assignment")
        # assert t.pretty().strip() == """
        assert (
            t.pretty().strip()
            == """
assignment
  dict
    assignment
      a
      1
    assignment
      b
      2
  1
""".strip()
        )


class TestArgs:
    def test_parse_args_positional_single(self):
        t = parser.parse("a,", start="args")
        assert (
            t.pretty().strip()
            == """
args\ta
""".strip()
        )

    def test_parse_args_positional_multiple(self):
        t = parser.parse("a b", start="args")
        assert (
            t.pretty().strip()
            == """
args
  a
  b
""".strip()
        )

    def test_parse_args_positional_mixed_commas(self):
        t = parser.parse("a b, c", start="args")
        assert (
            t.pretty().strip()
            == """
args
  a
  b
  c
""".strip()
        )

    def test_parse_args_keyed_single(self):
        t = parser.parse("a=1", start="args")
        assert (
            t.pretty().strip()
            == """
args
  assignment
    a
    1
""".strip()
        )

    def test_parse_args_keyed_single_trailing_comma(self):
        t = parser.parse("a=1,", start="args")
        assert (
            t.pretty().strip()
            == """
args
  assignment
    a
    1
""".strip()
        )

    def test_parse_args_positional_keyed(self):
        t = parser.parse("a b c=1 d=2", start="args")
        assert (
            t.pretty().strip()
            == """
args
  a
  b
  assignment
    c
    1
  assignment
    d
    2
""".strip()
        )

    def test_parse_args_positional_keyed_one_each(self):
        t = parser.parse("a c=1", start="args")
        assert (
            t.pretty().strip()
            == """
args
  a
  assignment
    c
    1
""".strip()
        )


class TestWrappedArgs:
    def test_parse_wrapped_args_keyed_single(self):
        t = parser.parse("(a=1)", start="wrapped_args")
        assert (
            t.pretty().strip()
            == """
wrapped_args
  assignment
    a
    1
""".strip()
        )

    def test_parse_wrapped_args_mixed(self):
        t = parser.parse("(0 1, a=A b=B c=C)", start="expression")
        assert (
            t.pretty().strip()
            == """
wrapped_args
  0
  1
  assignment
    a
    A
  assignment
    b
    B
  assignment
    c
    C
""".strip()
        )


class TestStatementList:
    def test_parse_statement_list_sep_newline(self):
        t = parser.parse("a b\nc d", start="statement_list")
        assert (
            t.pretty().strip()
            == """
statement_list
  args
    a
    b
  args
    c
    d
""".strip()
        )

    def test_parse_statement_list_sep_semicolon(self):
        t = parser.parse("a b; c d", start="statement_list")
        assert (
            t.pretty().strip()
            == """
statement_list
  args
    a
    b
  args
    c
    d
""".strip()
        )

    def test_parse_statement_list_single_statement(self):
        t = parser.parse("a=1;", start="statement_list")
        assert (
            t.pretty().strip()
            == """
statement_list
  args
    assignment
      a
      1
""".strip()
        )

    def test_does_not_parse_assignment(self):
        with pytest.raises(UnexpectedEOF):
            parser.parse("a=1", start="statement_list")


# Implement tests for execution_block. Its grammar definition is this:
# execution_block: "{" _WS* (statement_list | (_positional_args _keyed_args?)) _WS* "}"
class TestExecutionBlock:
    def test_parse_execution_block_statement_list(self):
        t = parser.parse("{a b; c d}", start="execution_block")
        assert (
            t.pretty().strip()
            == """
execution_block
  statement_list
    args
      a
      b
    args
      c
      d
""".strip()
        )

    def test_parse_execution_block_positional_args(self):
        t = parser.parse("{a b}", start="execution_block")
        assert (
            t.pretty().strip()
            == """
execution_block
  execution_block_single_statement
    a
    b
""".strip()
        )

    def test_parse_execution_block_only_assignments(self):
        t = parser.parse("{a=1; b=2}", start="execution_block")
        assert (
            t.pretty().strip()
            == """
execution_block
  statement_list
    args
      assignment
        a
        1
    args
      assignment
        b
        2
""".strip()
        )


class TestArray:
    def test_parse_array_empty(self):
        t = parser.parse("()", start="expression")
        assert (
            t.pretty().strip()
            == """
array
""".strip()
        )

    def test_parse_array_single_element(self):
        t = parser.parse("(a,)", start="expression")
        assert (
            t.pretty().strip()
            == """
array\ta
""".strip()
        )

    def test_parse_array_multiple_elements(self):
        t = parser.parse("(a, b, c, d)", start="expression")
        assert (
            t.pretty().strip()
            == """
array
  a
  b
  c
  d
""".strip()
        )

    def test_parse_array_multiple_elements_no_commas(self):
        t = parser.parse("(a b c d)", start="expression")
        assert (
            t.pretty().strip()
            == """
array
  a
  b
  c
  d
""".strip()
        )

    def test_parse_array_multiline(self):
        t = parser.parse("(\n    a,\n)", start="expression")
        assert (
            t.pretty().strip()
            == """
array\ta
""".strip()
        )


class TestDict:
    def test_parse_dict_empty(self):
        t = parser.parse("{}", start="expression")
        assert (
            t.pretty().strip()
            == """
dict
""".strip()
        )

    def test_parse_dict_single_pair(self):
        t = parser.parse("{a=1}", start="expression")
        assert (
            t.pretty().strip()
            == """
dict
  assignment
    a
    1
""".strip()
        )

    def test_parse_dict_multiple_pairs(self):
        t = parser.parse("{a=1 b=2 c=3}", start="expression")
        assert (
            t.pretty().strip()
            == """
dict
  assignment
    a
    1
  assignment
    b
    2
  assignment
    c
    3
""".strip()
        )

    def test_parse_dict_multiline(self):
        t = parser.parse("{\n    a=1,\n}", start="expression")
        assert (
            t.pretty().strip()
            == """
dict
  assignment
    a
    1
""".strip()
        )

    def test_do_not_parse_execution_block(self):
        with pytest.raises(UnexpectedCharacters):
            parser.parse("{\n    a=1\n}", start="dict")


class TestPath:
    def test_parse_path_simple(self):
        t = parser.parse("a.b.c", start="path")
        assert (
            t.pretty().strip()
            == """
path
  a
  b
  c
""".strip()
        )

    def test_parse_path_dot_string(self):
        t = parser.parse(".a", start="path")
        assert (
            t.pretty().strip()
            == """
path
  dots\t.
  a
""".strip()
        )

    def test_parse_path_string_dot(self):
        t = parser.parse("a.", start="path")
        assert (
            t.pretty().strip()
            == """
path
  a
  dots\t.
""".strip()
        )

    def test_parse_path_mixed_expressions(self):
        t = parser.parse("a.(-1.2).{x}.(1 a=2)", start="path")
        assert (
            t.pretty().strip()
            == """
path
  a
  -1.2
  execution_block
    execution_block_single_statement\tx
  wrapped_args
    1
    assignment
      a
      2
""".strip()
        )

    def test_parse_path_leading_dot(self):
        t = parser.parse(".a.b", start="path")
        assert (
            t.pretty().strip()
            == """
path
  dots\t.
  a
  b
""".strip()
        )

    def test_parse_path_trailing_dot(self):
        t = parser.parse("a.b.c.", start="path")
        assert (
            t.pretty().strip()
            == """
path
  a
  b
  c
  dots\t.
""".strip()
        )

    def test_parse_path_leading_trailing_dots(self):
        t = parser.parse("...a.b.c....", start="path")
        assert (
            t.pretty().strip()
            == """
path
  dots\t...
  a
  b
  c
  dots\t....
""".strip()
        )


class TestModule:
    def test_empty_module(self):
        t = parser.parse("", start="module")
        assert (
            t.pretty().strip()
            == """
module
""".strip()
        )

    def test_module_as_statement_list(self):
        t = parser.parse("a\n", start="module")
        assert (
            t.pretty().strip()
            == """
module
  statement_list\ta
""".strip()
        )

    def test_module_with_single_statement(self):
        t = parser.parse("a b", start="module")
        assert (
            t.pretty().strip()
            == """
module
  args
    a
    b
""".strip()
        )

    def test_module_with_single_expression(self):
        t = parser.parse("a", start="module")
        assert (
            t.pretty().strip()
            == """
module\ta
""".strip()
        )

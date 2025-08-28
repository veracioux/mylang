from mylang.parser import parser
from lark import Tree

_Tree_repr = Tree.__repr__

def Tree_repr(self: 'Tree'):
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
        assert t.data == "assignment"
        assert len(t.children) == 2

        assert t.children[0].type == "UNQUOTED_STRING"
        assert t.children[0].value == "a"

        assert t.children[1].type == "SIGNED_NUMBER"
        assert t.children[1].value == "1"

    def test_parse_assignment_spaced(self):
        t = parser.parse('"a" = 1', start="assignment")
        assert t.data == "assignment"
        assert len(t.children) == 2

        assert t.children[0].type == "ESCAPED_STRING"
        assert t.children[0].value == '"a"'

    def test_parse_assignment_complex_lvalue(self):
        t = parser.parse("(a b) = 1", start="assignment")
        assert t.data == "assignment"
        assert len(t.children) == 2

        assert t.children[0].data == "dict"
        assert len(t.children[0].children) == 2

        assert t.children[0].children[0].type == "UNQUOTED_STRING"
        assert t.children[0].children[0].value == "a"

        assert t.children[0].children[1].type == "UNQUOTED_STRING"
        assert t.children[0].children[1].value == "b"


class TestArgs:
    def test_parse_args_positional_single(self):
        t = parser.parse("a,", start="args")
        assert t.data == "args"
        assert len(t.children) == 1
        assert t.children[0].type == "UNQUOTED_STRING"
        assert t.children[0].value == "a"

    def test_parse_args_positional_multiple(self):
        t = parser.parse("a b", start="args")
        assert t.data == "args"
        assert len(t.children) == 2

        assert t.children[0].type == "UNQUOTED_STRING"
        assert t.children[0].value == "a"

        assert t.children[1].type == "UNQUOTED_STRING"
        assert t.children[1].value == "b"

    def test_parse_args_positional_mixed_commas(self):
        t = parser.parse("a b, c", start="args")
        assert t.data == "args"
        assert len(t.children) == 3

        assert t.children[0].type == "UNQUOTED_STRING"
        assert t.children[0].value == "a"

        assert t.children[1].type == "UNQUOTED_STRING"
        assert t.children[1].value == "b"

        assert t.children[2].type == "UNQUOTED_STRING"
        assert t.children[2].value == "c"

    def test_parse_args_keyed_single(self):
        t = parser.parse("a=1", start="args")

        assert t.data == "args"
        assert len(t.children) == 1

        assert t.children[0].data == "assignment"
        assert len(t.children[0].children) == 2

        assert t.children[0].children[0].type == "UNQUOTED_STRING"
        assert t.children[0].children[0].value == "a"

        assert t.children[0].children[1].type == "SIGNED_NUMBER"
        assert t.children[0].children[1].value == "1"

    def test_parse_args_keyed_single_trailing_comma(self):
        t = parser.parse("a=1,", start="args")

        assert t.data == "args"
        assert len(t.children) == 1

        assert t.children[0].data == "assignment"
        assert len(t.children[0].children) == 2

        assert t.children[0].children[0].type == "UNQUOTED_STRING"
        assert t.children[0].children[0].value == "a"

        assert t.children[0].children[1].type == "SIGNED_NUMBER"
        assert t.children[0].children[1].value == "1"

    def test_parse_args_positional_keyed(self):
        t = parser.parse("a b c=1 d=2", start="args")
        assert t.data == "args"
        assert len(t.children) == 4

        assert t.children[0].type == "UNQUOTED_STRING"
        assert t.children[0].value == "a"

        assert t.children[1].type == "UNQUOTED_STRING"
        assert t.children[1].value == "b"

        assert t.children[2].data == "assignment"
        assert len(t.children[2].children) == 2
        assert t.children[2].children[0].type == "UNQUOTED_STRING"
        assert t.children[2].children[0].value == "c"
        assert t.children[2].children[1].type == "SIGNED_NUMBER"
        assert t.children[2].children[1].value == "1"

        assert t.children[3].data == "assignment"
        assert len(t.children[2].children) == 2
        assert t.children[3].children[0].type == "UNQUOTED_STRING"
        assert t.children[3].children[0].value == "d"
        assert t.children[3].children[1].type == "SIGNED_NUMBER"
        assert t.children[3].children[1].value == "2"

    def test_parse_args_positional_keyed_one_each(self):
        t = parser.parse("a c=1", start="args")
        assert t.data == "args"
        assert len(t.children) == 2

        assert t.children[0].type == "UNQUOTED_STRING"
        assert t.children[0].value == "a"

        assert t.children[1].data == "assignment"
        assert len(t.children[1].children) == 2

        assert t.children[1].children[0].type == "UNQUOTED_STRING"
        assert t.children[1].children[0].value == "c"

        assert t.children[1].children[1].type == "SIGNED_NUMBER"
        assert t.children[1].children[1].value == "1"


class TestStatementList:
    def test_parse_statement_list_sep_newline(self):
        t = parser.parse("a b\nc d", start="statement_list")
        assert t.data == "statement_list"
        assert len(t.children) == 2

        assert t.children[0].data == "args"
        assert t.children[0].children[0].value == "a"
        assert t.children[0].children[1].value == "b"

        assert t.children[1].data == "args"
        assert t.children[1].children[0].value == "c"
        assert t.children[1].children[1].value == "d"


class TestPath:
    def test_parse_path_simple(self):
        t = parser.parse("a.b.c", start="path")
        assert t.data == "path"
        assert len(t.children) == 3

        assert t.children[0].type == "UNQUOTED_STRING"
        assert t.children[0].value == "a"

        assert t.children[1].type == "UNQUOTED_STRING"
        assert t.children[1].value == "b"

        assert t.children[2].type == "UNQUOTED_STRING"
        assert t.children[2].value == "c"

    def test_parse_path_dot_string(self):
        t = parser.parse('.a', start="path")
        assert t.pretty().strip() == """
path
  dots\t.
  a
""".strip()

    def test_parse_path_string_dot(self):
        t = parser.parse('a.', start="path")
        assert t.pretty().strip() == """
path
  a
  dots\t.
""".strip()

    def test_parse_path_mixed_expressions(self):
        t = parser.parse('a.(-1.2).{x}.(1 a=2)', start="path")
        assert t.pretty().strip() == """
path
  a
  -1.2
  execution_block
    statement_list	x
  dict
    1
    assignment
      a
      2
""".strip()

    def test_parse_path_leading_dot(self):
        t = parser.parse(".a.b", start="path")
        assert t.pretty().strip() == """
path
  dots\t.
  a
  b
""".strip()

    def test_parse_path_trailing_dot(self):
        t = parser.parse("a.b.c.", start="path")
        assert t.pretty().strip() == """
path
  a
  b
  c
  dots\t.
""".strip()

    def test_parse_path_leading_trailing_dots(self):
        t = parser.parse("...a.b.c....", start="path")
        assert t.pretty().strip() == """
path
  dots\t...
  a
  b
  c
  dots\t....
""".strip()

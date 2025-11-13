from lark import Token, Tree, UnexpectedEOF, UnexpectedCharacters
import pytest
import dataclasses
import textwrap
from mylang.parser import parser
from mylang.stdlib.core import Args


@dataclasses.dataclass
class Scenario:
    start: str
    """The starting rule for the parser."""
    source: str | None = None
    """The source code to parse. If None, the source is assumed to be the same as the basename of the scenario."""
    expected: str | None = None
    """The expected parse tree (or token value for terminals) as a string. If None, the expected is assumed to be the same as the source."""


# Defines test scenarios as a nested dictionary of arbitrary depth.
# Each leaf node is a Scenario that will be executed.
scenarios = {
    "BOOL": {
        "true": Scenario(start="expression"),
        "false": Scenario(start="expression"),
    },
    "NUMBER": {
        "0": Scenario(start="expression"),
        "123": Scenario(start="expression"),
        "-123": Scenario(start="expression"),
        "0.0": Scenario(start="expression"),
        "123.456": Scenario(start="expression"),
        "+123.456": Scenario(start="expression"),
        "-123.456": Scenario(start="expression"),
        "1.": Scenario(start="expression"),
        "-1.": Scenario(start="expression"),
        ".1": Scenario(start="expression"),
        "-.1": Scenario(start="expression"),
    },
    "assignment": {
        "a=1": Scenario(
            start="assignment",
            expected="""
            assignment
              a
              1
            """,
        ),
        '"a" = 1': Scenario(
            start="assignment",
            source='"a" = 1',
            expected="""
            assignment
              "a"
              1
            """,
        ),
        "complex_lvalue": Scenario(
            start="assignment",
            source="{a=1 b=2} = 1",
            expected="""
            assignment
              dict
                assignment
                  a
                  1
                assignment
                  b
                  2
              1
            """,
        ),
    },
    "operation": {
        "!+-a": Scenario(
            start="expression",
            expected="""
          prefix_operation
            !+-
            a
          """,
        ),
        "a!$+": Scenario(
            start="expression",
            expected="""
            postfix_operation
              a
              !$+
            """,
        ),
        "a +- b": Scenario(
            start="expression",
            expected="""
            binary_operation
              a
              +-
              b
            """,
        ),
        "a*/b": Scenario(
            start="expression",
            expected="""
            binary_operation
              a
              */
              b
            """,
        ),
        "ambiguity": {
            "-a + b": Scenario(
                start="expression",
                expected="""
                binary_operation
                  prefix_operation
                    -
                    a
                  +
                  b
                """,
            ),
            "-a!! + b": Scenario(
                start="expression",
                expected="""
                binary_operation
                  postfix_operation
                    prefix_operation
                      -
                      a
                    !!
                  +
                  b
                """,
            ),
            "-a!+b/": Scenario(
                start="expression",
                expected="""
                binary_operation
                  prefix_operation
                    -
                    a
                  !+
                  postfix_operation
                    b
                    /
                """,
            ),
        },
    },
    "args": {
        "positional_single": Scenario(
            start="args",
            source="a,",
            expected="""
            args\ta
            """,
        ),
        "positional_multiple": Scenario(
            start="args",
            source="a b",
            expected="""
            args
              a
              b
            """,
        ),
        "positional_mixed_commas": Scenario(
            start="args",
            source="a b, c",
            expected="""
            args
              a
              b
              c
            """,
        ),
        "keyed_single": Scenario(
            start="args",
            source="a=1",
            expected="""
            args
              assignment
                a
                1
            """,
        ),
        "keyed_single_trailing_comma": Scenario(
            start="args",
            source="a=1,",
            expected="""
            args
              assignment
                a
                1
            """,
        ),
        "positional_keyed": Scenario(
            start="args",
            source="a b c=1 d=2",
            expected="""
            args
              a
              b
              assignment
                c
                1
              assignment
                d
                2
            """,
        ),
        "positional_keyed": Scenario(
            start="args",
            source="a c=1",
            expected="""
            args
              a
              assignment
                c
                1
            """,
        ),
    },
    "wrapped_args": {
        "(a=1)": Scenario(
            start="wrapped_args",
            expected="""
            wrapped_args
              assignment
                a
                1
            """,
        ),
        "(0 1, a=A b=B c=C)": Scenario(
            start="expression",
            expected="""
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
            """,
        ),
    },
    "statement_list": {
        "sep_newline": Scenario(
            start="statement_list",
            source="a b\nc d",
            expected="""
            statement_list
              args
                a
                b
              args
                c
                d
            """,
        ),
        "sep_semicolon": Scenario(
            start="statement_list",
            source="a b; c d",
            expected="""
            statement_list
              args
                a
                b
              args
                c
                d
            """,
        ),
        "single_statement": Scenario(
            start="statement_list",
            source="a=1;",
            expected="""
            statement_list
              args
                assignment
                  a
                  1
            """,
        ),
    },
    "execution_block": {
        "{a b; c d}": Scenario(
            start="execution_block",
            expected="""
            execution_block
              statement_list
                args
                  a
                  b
                args
                  c
                  d
            """,
        ),
        "{a b}": Scenario(
            start="execution_block",
            expected="""
            execution_block
              execution_block_single_statement
                a
                b
            """,
        ),
        "{a=1; b=2}": Scenario(
            start="execution_block",
            expected="""
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
            """,
        ),
    },
    "array": {
        "()": Scenario(
            start="expression",
            expected="""
            array
            """,
        ),
        "(a,)": Scenario(
            start="expression",
            expected="""
            array\ta
            """,
        ),
        "(a, b, c, d)": Scenario(
            start="expression",
            expected="""
            array
              a
              b
              c
              d
            """,
        ),
        "(a b c d)": Scenario(
            start="expression",
            expected="""
            array
              a
              b
              c
              d
            """,
        ),
        "multiline": Scenario(
            start="expression",
            source="(\n    a,\n)",
            expected="""
            array\ta
            """,
        ),
    },
    "dict": {
        "{}": Scenario(
            start="expression",
            expected="""
            dict
            """,
        ),
        "{a=1}": Scenario(
            start="expression",
            expected="""
            dict
              assignment
                a
                1
            """,
        ),
        "{a=1 b=2 c=3}": Scenario(
            start="expression",
            expected="""
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
            """,
        ),
        "multiline": Scenario(
            start="expression",
            source="{\n    a=1,\n}",
            expected="""
            dict
              assignment
                a
                1
            """,
        ),
    },
    "path": {
        "a.b.c": Scenario(
            start="path",
            expected="""
            path
              a
              b
              c
            """,
        ),
        "a.(-1.2).{x}.(1 a=2)": Scenario(
            start="path",
            expected="""
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
            """,
        ),
        ".a.b": Scenario(
            start="path",
            expected="""
            path
              dots\t.
              a
              b
            """,
        ),
        "a.b.c.": Scenario(
            start="path",
            expected="""
            path
              a
              b
              c
              dots\t.
            """,
        ),
        "...a.b.c....": Scenario(
            start="path",
            expected="""
            path
              dots\t...
              a
              b
              c
              dots\t....
            """,
        ),
        "a.(b).1": Scenario(
            start="path",
            expected="""
            path
              a
              b
              1
            """,
        ),
    },
    "(path, operation)": {
        "+a.b": Scenario(
            start="expression",
            expected="""
            prefix_operation
              +
              path
                a
                b
            """,
        ),
        "+a.-b": Scenario(
            start="expression",
            expected="""
            prefix_operation
              +
              path
                a
                prefix_operation
                  -
                  b
            """,
        ),
        "+a.b!": Scenario(
            start="expression",
            expected="""
            postfix_operation
              prefix_operation
                +
                path
                  a
                  b
              !
            """,
        ),
        "a.b.1 + c.d": Scenario(
            start="expression",
            expected="""
            binary_operation
              path
                a
                b
                1
              +
              path
                c
                d
          """,
        ),
    },
    "module": {
        "empty": Scenario(
            start="module",
            source="",
            expected="""
            module
            """,
        ),
        "as_statement_list": Scenario(
            start="module",
            source="a\n",
            expected="""
            module
              statement_list\ta
            """,
        ),
        "with_single_statement": Scenario(
            start="module",
            source="a b",
            expected="""
            module
              args
                a
                b
            """,
        ),
        "with_single_expression": Scenario(
            start="module",
            source="a",
            expected="""
            module\ta
            """,
        ),
    },
}


def flatten_scenarios(scenarios, prefix=""):
    params = []
    ids = []
    for key, value in scenarios.items():
        if isinstance(key, type):
            key = key.__name__
        if isinstance(value, Scenario):
            source = value.source if value.source is not None else key
            expected = value.expected if value.expected is not None else source
            params.append((value.start, source, expected))
            ids.append(f"{prefix}|{key}" if prefix else key)
        else:
            sub_params, sub_ids = flatten_scenarios(value, f"{prefix}|{key}" if prefix else key)
            params.extend(sub_params)
            ids.extend(sub_ids)
    return params, ids


params, ids = flatten_scenarios(scenarios)


@pytest.mark.parametrize("start,source,expected", params, ids=ids)
def test_parser(start: str, source: str, expected: str):
    tree = parser.parse(source, start=start)
    assert isinstance(tree, (Token, Tree)), "Parsed result is neither a Token nor a Tree"
    if isinstance(tree, Token):
        assert tree.value == expected.strip()
    else:
        print("--- TREE ---")
        print(tree.pretty(), end="")
        print("--- END TREE ---")
        assert tree.pretty().strip() == textwrap.dedent(expected).strip()


# Additional tests that cannot be expressed as the simple scenarios above


class TestAdditionalScenarios:
    class TestStatementList:
        def test_does_not_parse_assignment(self):
            with pytest.raises(UnexpectedEOF):
                parser.parse("a=1", start="statement_list")

    class TestDict:
        def test_does_not_parse_execution_block(self):
            with pytest.raises(UnexpectedCharacters):
                parser.parse("{\n    a=1\n}", start="dict")

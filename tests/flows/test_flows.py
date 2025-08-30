from contextlib import contextmanager
import os

from pytest import CaptureFixture

from mylang.parser import STATEMENT_LIST, parser
from mylang.stdlib.core.func import StatementList
from mylang.transformer import Transformer
from mylang.stdlib.core._context import (
    nested_stack_frame,
)
from mylang.stdlib import builtins


@contextmanager
def read_module(*path_components: str):
    with open(os.path.join(os.path.dirname(__file__), *path_components)) as f:
        yield f.read()


def execute_module(*path_components: str):
    with (
        nested_stack_frame(builtins.create_locals_dict()),
        read_module(*path_components) as text,
    ):
        tree = parser.parse(text, start=STATEMENT_LIST)
        statement_list: StatementList = Transformer().transform(tree)
        statement_list.execute()


def test_empty(capsys: CaptureFixture[str]):
    execute_module("empty.my")

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_echo(capsys: CaptureFixture[str]):
    execute_module("echo.my")

    captured = capsys.readouterr()
    assert captured.out == "Hello world\n"
    assert captured.err == ""


def test_getset(capsys: CaptureFixture[str]):
    execute_module("getset.my")

    captured = capsys.readouterr()
    assert captured.out == "1\n"
    assert captured.err == ""


def test_lexical_scope(capsys: CaptureFixture[str]):
    execute_module("lexical_scope.my")

    captured = capsys.readouterr()
    assert captured.out.strip() == """
Function fun11 returned value: ('f1v1'='F1V1', 'f1v2'='F1V2', 'f11v1'='F11V1', 'f12v1'='unassigned')
Function f2 returned value: ('f1v1'='unassigned', 'f1v2'='unassigned', 'f11v1'='unassigned', 'f12v1'='unassigned')
In module scope, the values are: ('f1v1'='unassigned', 'f1v2'='unassigned', 'f11v1'='unassigned')
    """.strip()
    assert captured.err == ""


def test_recursion(capsys: CaptureFixture[str]):
    execute_module("recursion.my")
    captured = capsys.readouterr()

    assert captured.out == "Factorial of 5 is: 120\n"
    assert captured.err == ""


def test_operators(capsys: CaptureFixture[str]):
    execute_module("operators.my")
    captured = capsys.readouterr()

    assert captured.out.strip() == """
a == b is false
$x is 42
&x is 42
!x is false
1.5 - 4 is -2.5
0.3 * -4 is -1.2
2e2 + 3 is 203.0
1 + 2 + 3 is 6
    """.strip()
    assert captured.err == ""

def test_if_else(capsys: CaptureFixture[str]):
    execute_module("if_else.my")
    captured = capsys.readouterr()

    assert captured.out.strip() == """
{f 1} returned: _1
{f 2} returned: _2
{f 3} returned: _3
{f 4} returned: _4
    """.strip()
    assert captured.err == ""


def test_loop(capsys: CaptureFixture[str]):
    execute_module("loop.my")
    captured = capsys.readouterr()

    assert captured.out.strip() == """
x = 2
x = 1
x = 0
after 1st loop $x is 0
x = 1
after 2nd loop $x is 1
x = 3
after 3rd loop $x is 4
    """.strip()
    assert captured.err == ""


def test_path_getset(capsys: CaptureFixture[str]):
    execute_module("path_getset.my")
    captured = capsys.readouterr()

    assert captured.out.strip() == """
$dict is ('a'=1, 'b'=('c'=3, 'd'=4))
$dict.a is 1
$dict.b is ('c'=3, 'd'=4)
$dict.b.c is 3
$dict.b.d is 4
Setting dict.b.c to 5
$dict.b.c is now 5
    """.strip()
    assert captured.err == ""


def test_class(capsys: CaptureFixture[str]):
    execute_module("class.my")
    captured = capsys.readouterr()

    assert captured.out.strip() == """
created class <class Animal>
initializing Animal named animal
    """.strip()
    assert captured.err == ""

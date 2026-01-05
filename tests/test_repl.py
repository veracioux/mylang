# pylint: disable=missing-function-docstring,missing-module-docstring,invalid-name

from io import StringIO
import re
from textwrap import dedent
from typing import TextIO
from lark import UnexpectedCharacters, UnexpectedEOF
import pytest
from unittest.mock import MagicMock, patch

from mylang.stdlib.repl import REPL
from mylang.stdlib.core import undefined
from mylang.stdlib.core._context import StackFrame, current_stack_frame
from mylang.stdlib.core._utils import currently_called_func
from mylang.stdlib.core.primitive import Int
from mylang.stdlib.core.complex import String
from mylang.stdlib import builtins_


@pytest.fixture(autouse=True)
def isolate_stack_frame():
    """Isolate stack frame for each test to prevent interference."""
    reset_token_1 = current_stack_frame.set(
        StackFrame(builtins_.create_locals_dict(), parent=current_stack_frame.get())
    )
    reset_token_2 = currently_called_func.set(None)
    yield
    current_stack_frame.reset(reset_token_1)
    currently_called_func.reset(reset_token_2)


class TestREPL:
    """Test cases for the REPL class."""

    def test_init_default(self):
        """Test REPL initialization with default parameters."""
        repl = REPL()
        assert repl.normal_prompt == ">>> "
        assert repl.buffer.content == ""

    def test_init_custom_params(self):
        """Test REPL initialization with custom parameters."""
        repl = REPL(normal_prompt="custom> ")
        assert repl.normal_prompt == "custom> "
        assert repl.buffer.content == ""

    def test_print_prompt_new_input(self, capsys: pytest.CaptureFixture[str]):
        """Test print_prompt shows primary prompt for new input."""
        repl = REPL()
        repl.prompt()

        captured = capsys.readouterr()
        assert captured.out == ">>> "

    def test_print_prompt_continuation(self, capsys: pytest.CaptureFixture[str]):
        """Test print_prompt shows continuation prompt when buffer has content."""
        repl = REPL()
        repl.buffer.content = "some code"
        repl.prompt()
        captured = capsys.readouterr()
        assert captured.out == "... "

    def test_read_with_input(self):
        """Test read method with provided input string."""
        repl = REPL(input_source=StringIO("test input\n"))
        repl.read()
        assert repl.buffer.content == "test input\n"

    def test_read_empty_input(self):
        """Test read method with empty/whitespace-only input."""
        repl = REPL(input_source=StringIO(" "))
        repl.read()
        assert repl.buffer.content == " "

    def test_read_adds_to_buffer(self):
        """Test read method appends to existing buffer."""
        repl = REPL(input_source=StringIO("line 1\nline 2\n"))
        repl.read()
        assert repl.buffer.content == "line 1\n"
        repl.read()
        assert repl.buffer.content == "line 1\nline 2\n"

    def test_read_from_stdin(self):
        """Test read method reads from stdin when no input provided."""
        repl = REPL(input_source=StringIO("stdin input\n"))
        repl.read()
        assert repl.buffer.content == "stdin input\n"

    def test_read_empty_buffer(self):
        """Test read method handles EOFError."""
        repl = REPL(input_source=StringIO())
        repl.read()
        assert repl.buffer.content == ""

    def test_read_handles_ctrl_d(self):
        """Test read method handles Ctrl+D."""
        repl = REPL(input_source=StringIO("\x04"))
        with pytest.raises(EOFError):
            repl.read()
        assert repl.buffer.content == ""

    def test_eval_valid_statement(self):
        """Test eval method with valid statement."""
        repl = REPL()
        repl.buffer.content = "set x=42"
        result = repl.eval()
        assert result == undefined
        assert repl.buffer.content == ""  # Buffer should be cleared

    def test_eval_invalid_syntax(self):
        """Test eval method with invalid syntax."""
        repl = REPL()
        repl.buffer.content = "+++"
        with pytest.raises(UnexpectedCharacters):
            repl.eval()
        assert repl.buffer.content == ""  # Buffer should be cleared

    def test_eval_empty_buffer(self):
        """Test eval method with empty buffer."""
        repl = REPL()
        result = repl.eval()
        assert result is undefined
        assert repl.buffer.content == ""

    def test_eval_multiline_input(self, capsys: pytest.CaptureFixture[str]):
        """Test eval method handles multi-line input correctly."""
        repl = REPL()

        # First line - invalid syntax
        repl.buffer.content = "if true (\n"
        with pytest.raises(UnexpectedEOF):
            repl.eval()
        assert repl.buffer.content == "if true (\n"  # Buffer preserved

        # Add second line to complete the statement
        repl.buffer.content += 'echo "hello"\n'
        with pytest.raises(UnexpectedEOF):
            repl.eval()
        assert repl.buffer.content == 'if true (\necho "hello"\n'  # Buffer preserved

        repl.buffer.content += ")\n"
        assert repl.buffer.content == 'if true (\necho "hello"\n)\n'  # Buffer preserved
        result3 = repl.eval()

        assert result3 == undefined  # Statement executed
        assert repl.buffer.content == ""  # Buffer cleared
        captured = capsys.readouterr()
        assert captured.out == "hello\n"
        assert captured.err == ""

    def test_print_defined_result(self, capsys: pytest.CaptureFixture[str]):
        """Test print method prints defined results."""
        repl = REPL()
        result = Int(42)
        repl.print(result)

        captured = capsys.readouterr()
        assert captured.out == "42\n"
        assert captured.err == ""

    def test_print_undefined_result(self, capsys: pytest.CaptureFixture[str]):
        """Test print method doesn't print undefined results."""
        repl = REPL()
        repl.print(undefined)

        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""

    def test_print_string_result(self, capsys: pytest.CaptureFixture[str]):
        """Test print method with string results."""
        repl = REPL()
        result = String("hello world")
        repl.print(result)

        captured = capsys.readouterr()
        assert captured.out == "'hello world'\n"
        assert captured.err == ""

    def test_buffer_management(self):
        """Test buffer management across multiple operations."""
        repl = REPL(input_source=StringIO("line 1\nline 2\n"))

        # Start with empty buffer
        assert repl.buffer.content == ""

        # Add first line
        repl.read()
        assert repl.buffer.content == "line 1\n"

        # Add second line
        repl.read()
        assert repl.buffer.content == "line 1\nline 2\n"
        # Syntax error should clear buffer
        repl.buffer.content = "+\n"
        with pytest.raises(UnexpectedCharacters):
            repl.eval()
        assert repl.buffer.content == ""
        # Successful eval should clear buffer
        repl.buffer.content = "set x=42\n"
        repl.eval()
        assert repl.buffer.content == ""

    def test_run_loop_basic_flow(self, capsys: pytest.CaptureFixture[str]):
        """Test basic REPL run loop flow."""
        # Mock input sequence: valid input, then EOF
        repl = REPL(input_source=StringIO("set x=42\necho $x\n\x04"))

        # This should run the loop and exit on EOF
        repl.run()

        # Verify we got through the expected flow
        captured = capsys.readouterr()
        assert captured.out == dedent(
            """\
                >>> set x=42
                >>> echo $x
                42
                >>> ^D
            """
        )
        assert captured.err == ""

    def test_run_loop_keyboard_interrupts(self, capsys: pytest.CaptureFixture[str]):
        """Test REPL handles KeyboardInterrupt during input."""
        repl = REPL(input_source=StringIO("\x03\x04"))

        repl.run()

        captured = capsys.readouterr()
        # Should not print anything to stdout
        assert captured.out == ">>> ^C\n>>> ^D\n"
        assert captured.err == ""

    def test_run_loop_full(self, capsys: pytest.CaptureFixture[str]):
        """Test REPL handles parse errors gracefully."""
        scenario = re.sub(re.compile("^# .*\n", re.MULTILINE), "", dedent(
            """\
                >>> \t
                >>> set a = 5
                >>> ^C
                >>> dict1 = {
                ...   a = 1,
                ...   b = 2,
                ... }
                >>> echo a,
                ... b
                a b
                >>> dict2 = {
                ...   a = 1,
                ... ^C
                >>> get a
                5
                # >>>
                # >>> \x20\x20
                >>> \t
                >>> +++
                TODO: Syntax Error
                >>> try (
                ...   get b
                ... ) catch e (
                ...   Error (
                ...     echo b is not defined
                ...   )
                ... )
                b is not defined
                >>> ^D
            """
        ))
        expected_output = scenario

        input_chunks = []

        for line in scenario.splitlines(keepends=True):
            if line.startswith("# "):
                continue
            if line.startswith(">>> ") or line.startswith("... "):
                _, input = line.split(" ", 1)
                if input == "^C\n":
                    input_chunks.append("\x03")
                elif input == "^D\n":
                    input_chunks.append("\x04")
                else:
                    input_chunks.append(input)

        repl = REPL(input_source=StringIO("".join(input_chunks)))
        repl.run()

        captured = capsys.readouterr()

        assert captured.out == expected_output
        assert captured.err == ""

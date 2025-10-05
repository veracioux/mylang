# pylint: disable=missing-function-docstring,missing-module-docstring,invalid-name

import re
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
        assert repl.buffer_ == ""

    def test_init_custom_params(self):
        """Test REPL initialization with custom parameters."""
        repl = REPL(normal_prompt="custom> ")
        assert repl.normal_prompt == "custom> "
        assert repl.buffer_ == ""

    def test_print_prompt_new_input(self, capsys: pytest.CaptureFixture[str]):
        """Test print_prompt shows primary prompt for new input."""
        repl = REPL()
        repl.prompt()

        captured = capsys.readouterr()
        assert captured.out == ">>> "

    def test_print_prompt_continuation(self, capsys: pytest.CaptureFixture[str]):
        """Test print_prompt shows continuation prompt when buffer has content."""
        repl = REPL()
        repl.buffer_ = "some code"
        repl.prompt()
        captured = capsys.readouterr()
        assert captured.out == "... "

    def test_read_with_input(self):
        """Test read method with provided input string."""
        repl = REPL()
        result = repl.read("test input")
        assert result == "test input"
        assert repl.buffer_ == "test input\n"

    def test_read_empty_input(self):
        """Test read method with empty/whitespace-only input."""
        repl = REPL()
        result = repl.read("   ")
        assert result is None
        assert repl.buffer_ == ""

    def test_read_adds_to_buffer(self):
        """Test read method appends to existing buffer."""
        repl = REPL()
        repl.buffer_ = "line 1\n"
        result = repl.read("line 2")
        assert result == "line 2"
        assert repl.buffer_ == "line 1\nline 2\n"

    @patch("builtins.input")
    def test_read_from_stdin(self, mock_input):
        """Test read method reads from stdin when no input provided."""
        mock_input.return_value = "stdin input"
        repl = REPL()
        result = repl.read()
        assert result == "stdin input"
        assert repl.buffer_ == "stdin input\n"
        mock_input.assert_called_once()

    @patch("builtins.input")
    def test_read_eof_error(self, mock_input):
        """Test read method handles EOFError."""
        mock_input.side_effect = EOFError()
        repl = REPL()
        with pytest.raises(EOFError):
            repl.read()

    @patch("builtins.input")
    def test_read_keyboard_interrupt(self, mock_input):
        """Test read method handles KeyboardInterrupt."""
        mock_input.side_effect = KeyboardInterrupt()
        repl = REPL()
        with pytest.raises(KeyboardInterrupt):
            repl.read()

    def test_eval_valid_statement(self):
        """Test eval method with valid statement."""
        repl = REPL()
        repl.buffer_ = "set x=42"
        result = repl.eval()
        assert result == undefined
        assert repl.buffer_ == ""  # Buffer should be cleared

    def test_eval_invalid_syntax(self):
        """Test eval method with invalid syntax."""
        repl = REPL()
        repl.buffer_ = "+++"
        with pytest.raises(UnexpectedCharacters):
            result = repl.eval()
        assert repl.buffer_ == ""  # Buffer should be cleared

    def test_eval_empty_buffer(self):
        """Test eval method with empty buffer."""
        repl = REPL()
        result = repl.eval()
        assert result is undefined
        assert repl.buffer_ == ""

    def test_eval_multiline_input(self, capsys: pytest.CaptureFixture[str]):
        """Test eval method handles multi-line input correctly."""
        repl = REPL()

        # First line - invalid syntax
        repl.buffer_ = "if true (\n"
        with pytest.raises(UnexpectedEOF):
            repl.eval()
        assert repl.buffer_ == "if true (\n"  # Buffer preserved

        # Add second line to complete the statement
        repl.read('echo "hello"')
        with pytest.raises(UnexpectedEOF):
            repl.eval()
        assert repl.buffer_ == 'if true (\necho "hello"\n'  # Buffer preserved

        repl.read(')')
        assert repl.buffer_ == 'if true (\necho "hello"\n)\n'  # Buffer preserved
        result3 = repl.eval()

        assert result3 == undefined  # Statement executed
        assert repl.buffer_ == ""  # Buffer cleared

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
        repl = REPL()

        # Start with empty buffer
        assert repl.buffer_ == ""

        # Add first line
        repl.read("line 1")
        assert repl.buffer_ == "line 1\n"

        # Add second line
        repl.read("line 2")
        assert repl.buffer_ == "line 1\nline 2\n"

        # Syntax error should clear buffer
        repl.buffer_ = "+\n"
        with pytest.raises(UnexpectedCharacters):
            repl.eval()
        assert repl.buffer_ == ""

        # Successful eval should clear buffer
        repl.buffer_ = "set x=42\n"
        repl.eval()
        assert repl.buffer_ == ""

    @patch("builtins.input")
    def test_run_loop_basic_flow(self, mock_input: MagicMock, capsys: pytest.CaptureFixture[str]):
        """Test basic REPL run loop flow."""
        # Mock input sequence: valid input, then EOF
        mock_input.side_effect = ["set x=42", "echo $x", EOFError()]

        repl = REPL()

        # This should run the loop and exit on EOF
        repl.run()

        # Verify we got through the expected flow
        captured = capsys.readouterr()
        assert captured.out == ">>> >>> 42\n>>> "
        assert captured.err == ""

    @patch("builtins.input")
    def test_run_loop_keyboard_interrupts(self, mock_input, capsys: pytest.CaptureFixture[str]):
        """Test REPL handles KeyboardInterrupt during input."""
        mock_input.side_effect = [KeyboardInterrupt(), EOFError()]

        repl = REPL()

        repl.run()

        captured = capsys.readouterr()
        # Should not print anything to stdout
        assert captured.out == ">>> \nKeyboardInterrupt\n>>> "
        assert captured.err == ""

    @patch("builtins.input")
    def test_run_loop_full(self, mock_input, capsys: pytest.CaptureFixture[str]):
        """Test REPL handles parse errors gracefully."""
        # Special characters used:
        # \r indicates a new line that was output by the REPL
        # \0 separates the prompt from the user input on that line
        # ^C will be replaced by KeyboardInterrupt()
        # ^D will be replaced by EOFError()
        scenario = """
>>> \0set a = 5
>>> \0^C
\rKeyboardInterrupt
>>> \0dict1 = {
... \0  a = 1,
... \0  b = 2,
... \0}
>>> \0dict2 = {
... \0  a = 1,
... \0^C
\rKeyboardInterrupt
>>> \0echo a,
... \0b
a b
>>> \0get a
5
>>> \0
>>> \0\x20\x20
>>> \0\t
>>> \0+++
TODO: Syntax Error
>>> \0try (
>>> \0  get b
>>> \0) catch e (
>>> \0  Error (
>>> \0    echo b is not defined
>>> \0  )
>>> \0)
\rb is not defined
>>> \0^D
"""

        inputs = [
            (
                KeyboardInterrupt() if (raw := line.split("\0")[1]) == "^C"
                else EOFError() if raw == "^D"
                else raw
            )
            for line in scenario.strip().splitlines()
            if "\0" in line
        ]
        mock_input.side_effect = inputs

        expected_output = re.sub(r"\0.*?\n", "\0", scenario).replace("\r", "\n").replace("\0", "")

        repl = REPL()
        repl.run()

        captured = capsys.readouterr()
        assert captured.out.strip()[:6] == expected_output.strip()[:6]
        assert captured.err == ""

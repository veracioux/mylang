# pylint: disable=missing-function-docstring,missing-module-docstring,invalid-name

import pytest
from unittest.mock import patch
from io import StringIO

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
    reset_token_1 = current_stack_frame.set(StackFrame(builtins_.create_locals_dict(), parent=current_stack_frame.get()))
    reset_token_2 = currently_called_func.set(None)
    yield
    current_stack_frame.reset(reset_token_1)
    currently_called_func.reset(reset_token_2)


class TestREPL:
    """Test cases for the REPL class."""

    def test_init_default(self):
        """Test REPL initialization with default parameters."""
        repl = REPL()
        assert repl.prompt == ">>> "
        assert repl.execute_single_argument is False
        assert repl.buffer_ == ""

    def test_init_custom_params(self):
        """Test REPL initialization with custom parameters."""
        repl = REPL(prompt="custom> ", execute_single_argument=True)
        assert repl.prompt == "custom> "
        assert repl.execute_single_argument is True
        assert repl.buffer_ == ""

    @patch('builtins.print')
    def test_print_prompt_new_input(self, mock_print):
        """Test print_prompt shows primary prompt for new input."""
        repl = REPL()
        repl.print_prompt()
        mock_print.assert_called_once_with(">>> ", end="")

    @patch('builtins.print')
    def test_print_prompt_continuation(self, mock_print):
        """Test print_prompt shows continuation prompt when buffer has content."""
        repl = REPL()
        repl.buffer_ = "some code"
        repl.print_prompt()
        mock_print.assert_called_once_with("... ", end="")

    def test_read_with_input(self):
        """Test read method with provided input string."""
        repl = REPL()
        result = repl.read("test input")
        assert result == "test input"
        assert repl.buffer_ == "test input"

    def test_read_empty_input(self):
        """Test read method with empty/whitespace-only input."""
        repl = REPL()
        result = repl.read("   ")
        assert result is None
        assert repl.buffer_ == ""

    def test_read_adds_to_buffer(self):
        """Test read method appends to existing buffer."""
        repl = REPL()
        repl.buffer_ = "line 1"
        result = repl.read("line 2")
        assert result == "line 2"
        assert repl.buffer_ == "line 1\nline 2"

    @patch('builtins.input')
    def test_read_from_stdin(self, mock_input):
        """Test read method reads from stdin when no input provided."""
        mock_input.return_value = "stdin input"
        repl = REPL()
        result = repl.read()
        assert result == "stdin input"
        assert repl.buffer_ == "stdin input"
        mock_input.assert_called_once()

    @patch('builtins.input')
    def test_read_eof_error(self, mock_input):
        """Test read method handles EOFError."""
        mock_input.side_effect = EOFError()
        repl = REPL()
        with pytest.raises(EOFError):
            repl.read()

    @patch('builtins.input')
    def test_read_keyboard_interrupt(self, mock_input):
        """Test read method handles KeyboardInterrupt."""
        mock_input.side_effect = KeyboardInterrupt()
        repl = REPL()
        with pytest.raises(KeyboardInterrupt):
            repl.read()

    def test_eval_valid_expression(self):
        """Test eval method with valid expression."""
        repl = REPL()
        repl.buffer_ = '42'
        result = repl.eval()
        assert isinstance(result, Int)
        assert result.value == 42
        assert repl.buffer_ == ""  # Buffer should be cleared

    def test_eval_valid_statement(self):
        """Test eval method with valid statement."""
        repl = REPL()
        repl.buffer_ = 'set x=42'
        result = repl.eval()
        assert result == undefined
        assert repl.buffer_ == ""  # Buffer should be cleared

    def test_eval_single_expression_vs_statement(self):
        """Test difference between evaluating single expressions vs statements."""
        # Single expression should return the value
        repl1 = REPL(execute_single_argument=False)
        repl1.buffer_ = '42'
        result1 = repl1.eval()
        assert isinstance(result1, Int)
        assert result1.value == 42

        # With execute_single_argument=True, should execute as statement
        repl2 = REPL(execute_single_argument=True)
        repl2.buffer_ = '42'
        result2 = repl2.eval()
        assert result2 == undefined

    def test_eval_invalid_syntax(self):
        """Test eval method with invalid syntax."""
        repl = REPL()
        repl.buffer_ = 'invalid syntax +++'
        result = repl.eval()
        assert result is None  # Should return None on parse failure
        assert repl.buffer_ == 'invalid syntax +++'  # Buffer should NOT be cleared

    def test_eval_empty_buffer(self):
        """Test eval method with empty buffer."""
        repl = REPL()
        result = repl.eval()
        assert result is None
        assert repl.buffer_ == ""

    def test_eval_multiline_input(self):
        """Test eval method handles multi-line input correctly."""
        repl = REPL()
        # First line - invalid syntax
        repl.buffer_ = 'if true {'
        result1 = repl.eval()
        assert result1 is None
        assert repl.buffer_ == 'if true {'  # Buffer preserved

        # Add second line to complete the statement
        repl.read('echo "hello"')
        result2 = repl.eval()
        assert result2 == undefined  # Statement executed
        assert repl.buffer_ == ""  # Buffer cleared

    @patch('builtins.print')
    def test_print_defined_result(self, mock_print):
        """Test print method prints defined results."""
        repl = REPL()
        result = Int(42)
        repl.print(result)
        mock_print.assert_called_once_with(str(result._m_repr_()))

    @patch('builtins.print')
    def test_print_undefined_result(self, mock_print):
        """Test print method doesn't print undefined results."""
        repl = REPL()
        repl.print(undefined)
        mock_print.assert_not_called()

    @patch('builtins.print')
    def test_print_string_result(self, mock_print):
        """Test print method with string results."""
        repl = REPL()
        result = String("hello world")
        repl.print(result)
        mock_print.assert_called_once_with(str(result._m_repr_()))

    def test_buffer_management(self):
        """Test buffer management across multiple operations."""
        repl = REPL()

        # Start with empty buffer
        assert repl.buffer_ == ""

        # Add first line
        repl.read("line 1")
        assert repl.buffer_ == "line 1"

        # Add second line
        repl.read("line 2")
        assert repl.buffer_ == "line 1\nline 2"

        # Failed eval should preserve buffer
        repl.buffer_ = "invalid syntax"
        repl.eval()
        assert repl.buffer_ == "invalid syntax"

        # Successful eval should clear buffer
        repl.buffer_ = "42"
        repl.eval()
        assert repl.buffer_ == ""

    @patch('builtins.input')
    @patch('builtins.print')
    def test_run_loop_basic_flow(self, mock_print, mock_input):
        """Test basic REPL run loop flow."""
        # Mock input sequence: valid input, then EOF
        mock_input.side_effect = ["42", EOFError()]

        repl = REPL()

        # Mock the print calls we expect
        call_count = 0
        def mock_print_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call should be the welcome message
                assert "MyLang REPL" in args[0]
            elif call_count == 2:
                # Second call should be the help text
                assert "Enter:" in args[0]
            elif call_count == 3:
                # Third call should be the prompt
                assert args[0] == ">>> "
                assert kwargs == {"end": ""}
            elif call_count == 4:
                # Fourth call should be the result
                pass  # We don't know the exact format
            elif call_count == 5:
                # Fifth call should be the goodbye message
                assert "Goodbye!" in args[0]

        mock_print.side_effect = mock_print_side_effect

        # This should run the loop and exit on EOF
        repl.run()

        # Verify we got through the expected flow
        assert call_count >= 5

    @patch('builtins.input')
    @patch('builtins.print')
    def test_run_loop_keyboard_interrupt(self, mock_print, mock_input):
        """Test REPL handles KeyboardInterrupt during input."""
        mock_input.side_effect = KeyboardInterrupt()

        repl = REPL()

        # Capture print calls
        printed_messages = []
        def capture_print(*args, **kwargs):
            if args:
                printed_messages.append(args[0])

        mock_print.side_effect = capture_print

        repl.run()

        # Should print KeyboardInterrupt message
        assert "KeyboardInterrupt" in "".join(printed_messages)

    @patch('builtins.input')
    @patch('builtins.print')
    def test_run_loop_parse_error(self, mock_print, mock_input):
        """Test REPL handles parse errors gracefully."""
        mock_input.side_effect = ["invalid syntax +++", EOFError()]

        repl = REPL()

        printed_messages = []
        def capture_print(*args, **kwargs):
            if args:
                printed_messages.append(args[0])

        mock_print.side_effect = capture_print

        repl.run()

        # Should contain parse error message
        error_messages = [msg for msg in printed_messages if "Parse error" in msg]
        assert len(error_messages) > 0
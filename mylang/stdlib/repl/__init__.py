"""MyLang Read-Eval-Print Loop (REPL) implementation.

This module provides an interactive shell for MyLang programming language,
supporting multi-line input, syntax error recovery, and proper printing
of expressions and execution of statements.
"""

from contextlib import contextmanager
import os
import sys
import traceback
import termios

from lark import Tree, UnexpectedCharacters, UnexpectedEOF

from .state import InteractiveTextBuffer

from ..ui.keyboard import Key
from ..ui.term import ANSISequence, KeyChord, UnknownANSISequence, next_token

from ...parser import parser
from ..core import undefined, Object
from ...transformer import Transformer
from ..core.func import StatementList
from .. import builtins_
from ..core._context import StackFrame, current_stack_frame
from ..core._utils import repr_


class REPL:
    """Interactive Read-Eval-Print Loop for MyLang.

    Provides an interactive shell for executing MyLang code,
    supporting multi-line input and syntax error handling.

    Attributes:
        prompt (str): The primary prompt string (default: ">>> ")
        continuation_prompt (str): The prompt for continued lines (default: "... ")
        buffer_ (str): Internal buffer for accumulating multi-line input
    """

    def __init__(
        self,
        normal_prompt: str = ">>> ",
        continuation_prompt: str = "... ",
    ):
        """Initialize the REPL instance.

        Args:
            prompt: The prompt string to display for new input lines
        """
        self.normal_prompt = normal_prompt
        self.continuation_prompt = continuation_prompt
        self.buffer = InteractiveTextBuffer()

    def prompt(self):
        """Prompt the user for input."""
        if self.buffer.is_empty:
            self.print_normal_prompt()
        else:
            self.print_continuation_prompt()

    def print_normal_prompt(self):
        """Print the prompt for a new statement from the user."""
        print(self.normal_prompt, end="")
        sys.stdout.flush()

    def print_continuation_prompt(self):
        """Print the continuation prompt for multi-line input."""
        print(self.continuation_prompt, end="")

    def read(self):
        """Read input until a newline is encountered, while handling ANSI sequences.

        Returns:
            The input read from the user.

        Raises:
            EOFError: When Ctrl+D is pressed
            KeyboardInterrupt: When Ctrl+C is pressed
        """
        while True:
            token = next_token(sys.stdin)
            if isinstance(token, str):
                sys.stdout.write(token)
                sys.stdout.flush()
                self.buffer.insert_char(token)
            elif isinstance(token, KeyChord):
                self.handle_action(token)
            elif isinstance(token, UnknownANSISequence):
                sys.stdout.write(str(ANSISequence(token)))
                sys.stdout.flush()
            else:
                raise NotImplementedError

            if token == "\n":
                return

    def handle_action(self, action: KeyChord):
        def print_self(action: KeyChord):
            print(action.ansi.decode(), end="", flush=True)

        if action == Key.UP:
            if self.buffer.cursor.row > 0:
                self.buffer.move_cursor_by(-1, 0)
            print_self(action)
        elif action == Key.DOWN:
            print_self(action)
        elif action == Key.BACKSPACE:
            if self.buffer.cursor.col > 0:
                print("\b \b", end="", flush=True)
            self.buffer.delete_back()
        else:
            raise NotImplementedError(f"Unhandled REPL action: {action}")

    def eval(self) -> Object:
        """Evaluate the current buffer contents if they form valid MyLang code.

        Attempts to parse the buffer as a statement list. If successful, transforms
        and evaluates/executes the code based on the execute_single_argument setting.
        TODO: Support execute_single_argument setting or remove.

        Returns:
            The result of evaluation/execution, or None if parsing failed.

        Side effects:
            Clears the buffer on successful evaluation.
        Raises:
            UnexpectedCharacters: If the input has a syntax error.
            UnexpectedEOF: If the input is incomplete.
        """
        if self.buffer.content.strip():
            # Parse the buffer
            # Buffer is cleared on successful parsing or on syntax error
            try:
                tree = parser.parse(self.buffer.content + "\n", start="statement_list")
            except UnexpectedCharacters:
                self.buffer = InteractiveTextBuffer()
                raise
            self.buffer = InteractiveTextBuffer()

            # Print some debug info
            # FIXME: Remove before release
            if os.getenv("MYLANG_DEBUG"):
                _print_debug_info(tree)

            statement_list = Transformer().transform(tree)

            assert isinstance(
                statement_list, StatementList
            ), f"Expected parse+transform to give StatementList, got {type(statement_list)}"
            result = statement_list.execute()
            return result
        return undefined

    def print(self, result: Object):
        """Print the result of evaluation if it's not undefined.

        Args:
            result: The MyLang object to print
        """
        if result == undefined:
            pass
        else:
            print(repr_(result))

    def run(self):
        """Run the interactive REPL loop.

        Provides an interactive shell with the following controls:
        - Enter: Evaluate the current input as a statement list
        - Ctrl+C: Interrupt current input (clears buffer)
        - Ctrl+D: Exit the REPL

        The REPL supports multi-line input by continuing to read until
        valid syntax is entered.
        """
        with self._manage_tty(), StackFrame(builtins_.create_locals_dict(), parent=current_stack_frame.get()):
            while True:
                try:
                    self.prompt()
                    self.read()
                    result = self.eval()
                    self.print(result)
                # Fatal exceptions
                except EOFError:
                    print("^D")
                    break
                # Non-fatal exceptions
                except KeyboardInterrupt:
                    print("^C")
                    self.buffer = InteractiveTextBuffer()
                    continue
                except UnexpectedCharacters:
                    print("TODO: Syntax Error")
                    self.buffer = InteractiveTextBuffer()
                except UnexpectedEOF:
                    # Incomplete input, continue reading
                    pass
                except Exception:
                    self.buffer = InteractiveTextBuffer()
                    traceback.print_exc()

    @contextmanager
    def _manage_tty(self):
        """Manage TTY settings for the REPL."""
        stdin = sys.stdin
        stdin_fd = stdin.fileno()
        attrs = old_settings = termios.tcgetattr(stdin_fd)
        attrs[3] &= ~(termios.ICANON | termios.ECHO)
        termios.tcsetattr(stdin_fd, termios.TCSANOW, attrs)
        try:
            yield
        finally:
            termios.tcsetattr(stdin_fd, termios.TCSADRAIN, old_settings)


# FIXME: Remove before release
def _print_debug_info(tree: Tree) -> None:
    """Print debug information about a parsed syntax tree.

    Args:
        tree: The parsed syntax tree to display
    """
    tree_str = tree.pretty() if isinstance(tree, Tree) else str(tree)
    print(
        "  Syntax tree:",
        "\n    ".join(line for line in tree_str.splitlines()),
        sep="\n    ",
    )

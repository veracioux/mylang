"""MyLang Read-Eval-Print Loop (REPL) implementation.

This module provides an interactive shell for MyLang programming language,
supporting multi-line input, syntax error recovery, and proper printing
of expressions and execution of statements.
"""

import io
import os
import sys
import traceback
from typing import Optional

from lark import Tree, UnexpectedCharacters, UnexpectedEOF

from ...parser import parser
from ..core import undefined, Object
from ...transformer import Transformer
from ..core.func import StatementList
from .. import builtins_
from ..core._context import StackFrame, current_stack_frame


# FIXME: Remove before release
# This is for debugging purposes, mostly so I can feed it to an LLM
_parse_history_file = "parse-history.txt"


class REPL:
    """Interactive Read-Eval-Print Loop for MyLang.

    Provides an interactive shell for executing MyLang code,
    supporting multi-line input and syntax error handling.

    Attributes:
        prompt (str): The primary prompt string (default: ">>> ")
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
        self.buffer_ = ""

    def prompt(self):
        """Prompt the user for input."""
        if self.buffer_:
            self.print_continuation_prompt()
        else:
            self.print_normal_prompt()

    def print_normal_prompt(self):
        """Print the prompt for a new statement from the user."""
        print(self.normal_prompt, end="")

    def print_continuation_prompt(self):
        """Print the continuation prompt for multi-line input."""
        print(self.continuation_prompt, end="")

    def read(self, input_: Optional[str] = None) -> Optional[str]:
        """Read a line of input and add it to the buffer.

        Args:
            input_: Optional input string (for testing). If None, reads from stdin.

        Returns:
            The input line, or None if empty.

        Raises:
            EOFError: When Ctrl+D is pressed
            KeyboardInterrupt: When Ctrl+C is pressed
        """
        line = input_ or input()
        if not line.strip():
            return None
        # Add line to buffer
        self.buffer_ += line + "\n"
        return line

    def eval(self) -> Object:
        """Evaluate the current buffer contents if they form valid MyLang code.

        Attempts to parse the buffer as a statement list. If successful, transforms
        and evaluates/executes the code based on the execute_single_argument setting.

        Returns:
            The result of evaluation/execution, or None if parsing failed.

        Side effects:
            Clears the buffer on successful evaluation.
        Raises:
            UnexpectedCharacters: If the input has a syntax error.
            UnexpectedEOF: If the input is incomplete.
        """
        if self.buffer_.strip():
            # Parse the buffer
            # Buffer is cleared on successful parsing or on syntax error
            try:
                tree = parser.parse(self.buffer_ + "\n", start="statement_list")
            except UnexpectedCharacters:
                self.buffer_ = ""
                raise
            self.buffer_ = ""

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
            print(str(result._m_repr_()))

    def run(self):
        """Run the interactive REPL loop.

        Provides an interactive shell with the following controls:
        - Enter: Evaluate the current input as a statement list
        - Ctrl+C: Interrupt current input (clears buffer)
        - Ctrl+D: Exit the REPL

        The REPL supports multi-line input by continuing to read until
        valid syntax is entered.
        """
        # TODO: Use with to clean up stack frame
        current_stack_frame.set(StackFrame(builtins_.create_locals_dict(), parent=current_stack_frame.get()))

        while True:
            try:
                self.prompt()
                self.read()
                result = self.eval()
                self.print(result)
            # Fatal exceptions
            except EOFError:
                # Ctrl+D pressed
                break
            # Non-fatal exceptions
            except KeyboardInterrupt:
                # Ctrl+C pressed
                print("\nKeyboardInterrupt")
                self.buffer_ = ""
                continue
            except UnexpectedCharacters as e:
                print(f"TODO: Syntax Error")
                self.buffer_ = ""
            except UnexpectedEOF as e:
                # Incomplete input, continue reading
                pass
            except Exception as e:
                self.buffer_ = ""
                traceback.print_exc()


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
    with open(_parse_history_file, "a", encoding="utf-8") as f:
        f.write(tree_str + "\n")

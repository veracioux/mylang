"""MyLang Read-Eval-Print Loop (REPL) implementation.

This module provides an interactive shell for MyLang programming language,
supporting multi-line input, syntax error recovery, and proper printing
of expressions and execution of statements.
"""

import traceback
from typing import Optional

from lark import ParseError, Tree, UnexpectedCharacters

from ...parser import parser
from ..core import Args, undefined, Object
from ..core.base import IncompleteExpression
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
        prompt: str = ">>> ",
    ):
        """Initialize the REPL instance.

        Args:
            prompt: The prompt string to display for new input lines
        """
        self.prompt = prompt
        self.buffer_ = ""

    def print_prompt(self):
        """Print the appropriate prompt based on current buffer state.

        Shows ">>> " for new input or "... " for continuation lines.
        """
        if self.buffer_:
            prompt = "... "
        else:
            prompt = self.prompt
        print(prompt, end="")

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
        try:
            line = input_ or input()
            if not line.strip():
                return None
            # Add line to buffer
            if self.buffer_:
                self.buffer_ += "\n" + line
            else:
                self.buffer_ = line
            return line
        except EOFError:
            raise EOFError("Ctrl+D pressed")
        except KeyboardInterrupt:
            raise KeyboardInterrupt("Ctrl+C pressed")

    def eval(self) -> Optional[Object]:
        """Evaluate the current buffer contents if they form valid MyLang code.

        Attempts to parse the buffer as a statement list. If successful, transforms
        and evaluates/executes the code based on the execute_single_argument setting.

        Returns:
            The result of evaluation/execution, or None if parsing failed.

        Side effects:
            Clears the buffer on successful evaluation.
        """
        try:
            if self.buffer_.strip():
                tree = parser.parse(self.buffer_ + "\n", start="statement_list")
                _print_debug_info(tree)
                self.buffer_ = ""
                statement_list = Transformer().transform(tree)

                assert isinstance(
                    statement_list, StatementList
                ), f"Expected parse+transform to give StatementList, got {type(statement_list)}"

                return statement_list.execute()
        except (ParseError, UnexpectedCharacters):
            # If parsing fails, continue collecting input
            # This allows multi-line input
            pass
        return None

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
        print("MyLang REPL")
        print("Enter: evaluate | Ctrl+D: exit")
        print()

        # TODO: Use with to clean up stack frame
        current_stack_frame.set(StackFrame(builtins_.create_locals_dict(), parent=current_stack_frame.get()))

        # TODO: Handle Alt+Enter to insert a newline without evaluating

        while True:
            try:
                self.print_prompt()
                self.read()
                result = self.eval()
                if result is not None:
                    self.print(result)
            except EOFError:
                # Ctrl+D pressed
                print("\nGoodbye!")
                break
            except KeyboardInterrupt:
                # Ctrl+C pressed
                print("\nKeyboardInterrupt")
                self.buffer_ = ""
                continue
            except ParseError as e:
                print(f"Parse error: {e}")
                self.buffer_ = ""
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

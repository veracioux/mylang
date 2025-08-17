#!/usr/bin/env python3
import sys
import termios
import tty

from lark import Token, Tree, UnexpectedCharacters
from mylang.parser import parser
from lark.exceptions import ParseError


def repl():
    """Interactive REPL for mylang.

    - Enter: evaluate the current input as statement_list
    - Alt+Enter: insert newline without evaluation
    - Ctrl+C: interrupt current input
    - Ctrl+D: exit REPL
    """
    print("MyLang REPL")
    print("Enter: evaluate | Alt+Enter: newline (TODO) | Ctrl+D: exit")
    print()

    buffer = ""

    # TODO: Handle Alt+Enter to insert a newline without evaluating

    while True:
        try:
            if buffer:
                prompt = "... "
            else:
                prompt = ">>> "

            line = input(prompt)

            # Add line to buffer
            if buffer:
                buffer += "\n" + line
            else:
                buffer = line

            # Evaluate only when the buffer forms a valid statement_list
            # Otherwise insert a newline
            try:
                if buffer.strip():
                    tree = parser.parse(buffer, start="statement_list")
                    if isinstance(tree, Tree):
                        print(tree.pretty())
                    elif isinstance(tree, Token):
                        print(tree.value)
                    buffer = ""
            except (ParseError, UnexpectedCharacters) as e:
                print(e)
                buffer += "\n"
                # If parsing fails, continue collecting input
                # This allows multi-line input
                continue

        except EOFError:
            # Ctrl+D pressed
            print("\nGoodbye!")
            break
        except KeyboardInterrupt:
            # Ctrl+C pressed
            print("\nKeyboardInterrupt")
            buffer = ""
            continue
        except ParseError as e:
            print(f"Parse error: {e}")
            buffer = ""
        except Exception as e:
            print(f"Error: {e}")
            buffer = ""


if __name__ == "__main__":
    repl()

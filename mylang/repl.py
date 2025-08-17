#!/usr/bin/env python3

from lark import Tree, UnexpectedCharacters
from mylang.parser import parser
from lark.exceptions import ParseError


# This is for debugging purposes, mostly so I can feed it to an LLM
_parse_history_file = "parse-history.txt"


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

    buf = ""

    # TODO: Handle Alt+Enter to insert a newline without evaluating

    while True:
        try:
            if buf:
                prompt = "... "
            else:
                prompt = ">>> "

            line = input(prompt)

            # Add line to buffer
            if buf:
                buf += "\n" + line
            else:
                buf = line

            # Evaluate only when the buffer forms a valid statement_list
            # Otherwise insert a newline
            try:
                if buf.strip():
                    tree = parser.parse(buf, start="statement_list")
                    tree_str = tree.pretty() if isinstance(tree, Tree) else str(tree)
                    print(tree_str)
                    with open(_parse_history_file, "a", encoding="utf-8") as f:
                        f.write(prompt + buf + "\n")
                        f.write(tree_str + "\n")
                    buf = ""
            except (ParseError, UnexpectedCharacters) as e:
                buf += "\n"
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
            buf = ""
            continue
        except ParseError as e:
            print(f"Parse error: {e}")
            buf = ""
        except Exception as e:
            print(f"Error: {e}")
            buf = ""


if __name__ == "__main__":
    repl()

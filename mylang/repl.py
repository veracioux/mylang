#!/usr/bin/env python3

import traceback

from lark import ParseError, Tree, UnexpectedCharacters

from mylang.parser import parser
from mylang.stdlib.core import Args, undefined
from mylang.stdlib.core.base import Object
from mylang.transformer import StatementList, Transformer

import mylang.stdlib.builtins

# Imported for side effects
_ = mylang.stdlib.builtins


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

            if not line.strip():
                continue

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
                    # print("\tSyntax tree:", tree_str, sep="\n\t")
                    with open(_parse_history_file, "a", encoding="utf-8") as f:
                        f.write(prompt + buf + "\n")
                        f.write(tree_str + "\n")
                    buf = ""
            except (ParseError, UnexpectedCharacters):
                buf += "\n"
                # If parsing fails, continue collecting input
                # This allows multi-line input
                continue

            transformed = Transformer().transform(tree)
            # print("\tTransformed:", repr(transformed), sep="\n\t")
            try:
                evaluated = evaluate(transformed)
                repl_print(evaluated)
            except Exception as e:
                buf = ""
                traceback.print_exc()

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
            buf = ""
            raise e


def evaluate(statements: StatementList) -> Object:
    if len(statements) == 1 and not isinstance(statements[0], Args):
        return statements[0]
    else:
        return statements.execute()


def repl_print(obj: Object) -> None:
    """Prints the object in a human-readable format."""
    if obj == undefined:
        pass
    else:
        print(str(obj._m_repr_()))

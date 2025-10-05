"""Main module for MyLang CLI."""

import sys

from mylang.stdlib.repl import REPL
from mylang.parser import parser
from mylang.stdlib.core.func import StatementList
from mylang.transformer import Transformer
from mylang.stdlib.core._context import StackFrame, current_stack_frame


def main():
    """Main entry point for the MyLang interpreter."""
    input_file_data: str | None = None
    if len(sys.argv) == 2:
        with open(sys.argv[1], "r", encoding="utf-8") as f:
            input_file_data = f.read()
    # FIXME: Remove this:
    elif len(sys.argv) > 2:
        with open(sys.argv[-1], "r", encoding="utf-8") as f:
            input_file_data = f.read()
    elif not sys.stdin.isatty():
        input_file_data = sys.stdin.read()

    if input_file_data:
        from mylang.stdlib import builtins_

        tree = parser.parse(input_file_data, start="module")
        # TODO: Remove
        print("Syntax tree:\n", tree.pretty())
        with StackFrame(builtins_.create_locals_dict(), parent=current_stack_frame.get()):
            statement_list: StatementList = Transformer().transform(tree)
            statement_list.execute()
    else:
        print("MyLang REPL")
        print("Enter: evaluate | Ctrl+D: exit")
        print()
        REPL().run()
        print("\nGoodbye!")


if __name__ == "__main__":
    main()

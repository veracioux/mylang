"""Main module for MyLang CLI."""

import sys
from mylang.stdlib.repl import REPL
from mylang.parser import parser
from mylang.stdlib.core.func import StatementList
from mylang.transformer import Transformer
from mylang.stdlib.core._context import StackFrame, current_stack_frame
from mylang.stdlib import builtins_
from mylang.cli import CLI, FileInputSource, TextInputSource


def main():
    """Main CLI entry point."""
    cli = CLI()
    cli.parse()
    input_source = cli.get_input_source()

    # Import here to avoid circular imports
    if input_source is None:
        print("MyLang REPL")
        print("Enter: evaluate | Ctrl+D: exit")
        print()
        REPL().run()
        print("\nGoodbye!")
    else:
        input_file_data: str
        # Get the code content
        if isinstance(input_source, FileInputSource):
            with open(input_source.file_path, "r", encoding="utf-8") as f:
                input_file_data = f.read()
        elif isinstance(input_source, TextInputSource):
            input_file_data = input_source.text
        else:
            raise NotImplementedError

        # Execute the code
        tree = parser.parse(input_file_data, start="module")
        # TODO: Remove debug print
        print("Syntax tree:\n", tree.pretty())
        with StackFrame(builtins_.create_locals_dict(), parent=current_stack_frame.get()):
            statement_list: StatementList = Transformer().transform(tree)
            statement_list.execute()


if __name__ == "__main__":
    sys.exit(main())

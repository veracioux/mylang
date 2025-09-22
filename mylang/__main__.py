from mylang.repl import repl
import sys
from mylang.parser import STATEMENT_LIST, parser
from mylang.stdlib.core.func import StatementList
from mylang.transformer import Transformer
from mylang.stdlib.core._context import StackFrame, current_stack_frame


def main():
    input_file_data: str = None
    if len(sys.argv) == 2:
        with open(sys.argv[1], "r") as f:
            input_file_data = f.read()
    # FIXME: Remove this:
    elif len(sys.argv) > 2:
        with open(sys.argv[-1], "r") as f:
            input_file_data = f.read()
    elif not sys.stdin.isatty():
        input_file_data = sys.stdin.read()

    if input_file_data:
        from mylang.stdlib import builtins_

        # TODO: Use with to clean up stack frame
        current_stack_frame.set(
            StackFrame(builtins_.create_locals_dict(), parent=current_stack_frame.get())
        )

        tree = parser.parse(input_file_data, start=STATEMENT_LIST)
        # TODO: Remove
        print("Syntax tree:\n", tree.pretty())
        statement_list: StatementList = Transformer().transform(tree)
        statement_list.execute()
    else:
        repl()


if __name__ == "__main__":
    main()

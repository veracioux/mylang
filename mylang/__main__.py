from mylang.repl import repl
import sys
from mylang.parser import STATEMENT_LIST, parser
from mylang.transformer import Transformer


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
        import mylang.stdlib.builtins

        # Import for side effects
        _ = mylang.stdlib.builtins
        tree = parser.parse(input_file_data, start=STATEMENT_LIST)
        # TODO: Remove
        # print("Syntax tree:\n", tree.pretty())
        statement_list = Transformer().transform(tree)
        statement_list.execute()
    else:
        repl()


if __name__ == "__main__":
    main()

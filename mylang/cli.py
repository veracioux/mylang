"""Command line interface for MyLang using argparse."""

import abc
import argparse
import sys

__all__ = ("CLI", "FileInputSource", "TextInputSource")


class InputSource(abc.ABC):
    pass


class FileInputSource(InputSource):
    def __init__(self, file_path: str):
        self.file_path = file_path


class TextInputSource(InputSource):
    def __init__(self, text: str):
        self.text = text


class CLI:
    """Command line interface for MyLang."""

    def __init__(self):
        self.parser = argparse.ArgumentParser(prog="mylang", description="MyLang programming language interpreter")

        self.parser.add_argument("-c", "--command", help="Execute the given code string")

        self.parser.add_argument("file", nargs="?", help="File to execute (optional)")

        self._parsed_args: argparse.Namespace

    def parse(self):
        """Parse command line arguments."""
        self._parsed_args = self.parser.parse_args()

    def get_input_source(self):
        """
        Determine the input source based on parsed arguments.

        Returns:
            InputSource or None if REPL should be started.
        """
        args = self._parsed_args

        if args.command:
            return TextInputSource(args.command)

        if args.file:
            return FileInputSource(args.file)

        if not sys.stdin.isatty():
            return TextInputSource(sys.stdin.read())

        # No arguments and stdin is a tty - start REPL
        return None

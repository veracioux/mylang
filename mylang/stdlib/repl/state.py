import dataclasses
from typing import Literal


@dataclasses.dataclass
class Point:
    row: int
    col: int

    def moved(self, delta_row: int, delta_col: int) -> "Point":
        return Point(self.row + delta_row, self.col + delta_col)


@dataclasses.dataclass
class InteractiveTextBuffer:
    _content: list[str] = dataclasses.field(default_factory=list)
    cursor = Point(0, 0)

    def move_cursor_by(self, delta_row: int, delta_col: int):
        moved_cursor = self.cursor.moved(delta_row, delta_col)
        if moved_cursor in self:
            self.cursor = moved_cursor

    def insert_char(self, char: str):
        """Insert character at the current cursor position."""
        moved_cursor = self.cursor.moved(0, 1)
        if moved_cursor in self:
            self._content[moved_cursor.row] = _str_replace(self._content[moved_cursor.row], self.cursor.col, char)
        elif not self._content:
            self._content.append(char)
        else:
            self._content[self.cursor.row] += char
        self.cursor = moved_cursor

    def delete_back(self):
        """Delete character under cursor and move the cursor back."""
        if self.cursor.col == 0 and self.cursor.row == 0:
            return  # Nothing to delete
        if self.cursor.col == 0:
            # Move to end of previous line
            prev_line = self._content[self.cursor.row - 1]
            self.cursor = Point(self.cursor.row - 1, len(prev_line) - 1)
        else:
            self._content[self.cursor.row] = _str_replace(self._content[self.cursor.row], self.cursor.col - 1, "")
            self.move_cursor_by(0, -1)

    @property
    def content(self) -> str:
        return "\n".join(self._content)

    @property
    def is_empty(self) -> bool:
        return len(self._content) == 0

    @property
    def rows(self):
        return len(self._content)

    @property
    def cols(self):
        return max(len(line) for line in self.content.splitlines())

    def __contains__(self, item: str | Point) -> bool:
        return (
            item in self.content
            if isinstance(item, str)
            else (0 <= item.row < self.rows and 0 <= item.col <= len(self._content[item.row]))
        )


def _str_replace(s: str, index: int, replacement: str) -> str:
    return s[:index] + replacement + s[index + 1 :]

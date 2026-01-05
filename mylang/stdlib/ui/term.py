from typing import TextIO
from .keyboard import Key, KeyChord as _KeyChord


class KeyChord(_KeyChord):
    @property
    def ansi(self):
        return _chord_to_ansi[self]


class ANSISequence(bytes):
    def __str__(self):
        if self[0] == 0:
            return "^@"
        elif self[0] in range(2, 0x1F):
            return "^" + chr(self[0] + 64)
        elif self[0] == 0x7F:
            return "^?"
        return self.replace(b"\x1b", b"^[").decode()


_chord_to_ansi: dict[KeyChord, bytes] = {
    KeyChord(Key.UP): b"\x1b[A",
    KeyChord(Key.DOWN): b"\x1b[B",
    KeyChord(Key.LEFT): b"\x1b[D",
    KeyChord(Key.RIGHT): b"\x1b[C",
    KeyChord(Key.BACKSPACE): b"\x7f",
}


_ansi_to_chord = {v: k for k, v in _chord_to_ansi.items()}


class UnknownANSISequence(bytes):
    pass


Token = str | KeyChord | UnknownANSISequence | None


def next_token(input: TextIO) -> Token:
    buffer = ""

    def get_next():
        nonlocal buffer
        char = input.read(1)
        buffer += char
        return char

    char = get_next()

    if char == "":
        return None

    if char == "\x04":  # ^D (Ctrl+D)
        raise EOFError

    if char == "\x03":  # ^C (Ctrl+C)
        raise KeyboardInterrupt

    if char in ("\t", "\n"):
        return char

    # Handle ANSI escape sequences - a successful match must return
    if char == "\x1b":
        next_ = get_next()
        if next_ == "[":
            get_next()
            key_chord = _ansi_to_chord.get(buffer.encode())
            if key_chord:
                return key_chord
    elif ord(char) in range(2, 0x1F) or char == "\0" or char == "\x7f":
        return _ansi_to_chord.get(char.encode(), UnknownANSISequence(char.encode()))

    # No ANSI sequence matched, return the character
    return buffer

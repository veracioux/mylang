import abc
from typing import final


class Key(abc.ABC):
    UP: "RegularKey"
    DOWN: "RegularKey"
    LEFT: "RegularKey"
    RIGHT: "RegularKey"
    BACKSPACE: "RegularKey"

    def __init__(self, code: str):
        self.code = code.upper()

    def __hash__(self):
        return hash((Key, self.code.upper()))

    def __eq__(self, other):
        return (isinstance(other, Key) and self.code == other.code.upper() or isinstance(other, str) and self.code == other.upper())

    def __repr__(self):
        return f"{self.__class__.__name__}.{self.code.upper()}"


class RegularKey(Key):
    def __hash__(self):
        return hash((RegularKey, self.code.upper()))

    def __eq__(self, other):
        return isinstance(other, RegularKey) and self.code == other.code.upper()


class ModifierKey(Key):
    def __hash__(self):
        return hash((ModifierKey, self.code.upper()))

    def __eq__(self, other):
        return isinstance(other, ModifierKey) and self.code == other.code.upper()


Key.UP = RegularKey("UP")
Key.DOWN = RegularKey("DOWN")
Key.LEFT = RegularKey("LEFT")
Key.RIGHT = RegularKey("RIGHT")
Key.BACKSPACE = RegularKey("BACKSPACE")


class KeyChord:
    def __init__(self, *keys: Key | str):
        assert len(keys) >= 1
        normalized_keys = (
            *(key if isinstance(key, Key) else RegularKey(key) for key in keys[:-1]),
            keys[-1] if isinstance(keys[-1], Key) else RegularKey(keys[-1]),
        )
        assert all(isinstance(key, ModifierKey) for key in normalized_keys[:-1])
        assert isinstance(normalized_keys[-1], RegularKey)
        self.keys = normalized_keys

    @final
    def __hash__(self):
        return hash((KeyChord, self.keys))

    @final
    def __eq__(self, other):
        return isinstance(other, KeyChord) and self.keys == other.keys or isinstance(other, Key) and len(self.keys) == 1 and self.keys[0] == other

    def __repr__(self):
        return f"{self.__class__.__name__}({', '.join(repr(key.code) for key in self.keys)})"
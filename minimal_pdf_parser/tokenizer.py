#  Minimal PDF Parser - Another Python PDF parser
#     Copyright (C) 2023 J. Férard <https://github.com/jferard>
#
#     This file is part of Minimal PDF Parser.
#
#     Minimal PDF Parser is free software: you can redistribute it and/or
#     modify it under the terms of the GNU General Public License as published
#     by the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.
#
#     Minimal PDF Parser is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program.  If not, see <http://www.gnu.org/licenses/>.
import struct
from abc import ABC, abstractmethod
from typing import NamedTuple, BinaryIO, cast, Any, Iterator

from base import (
    OpenDictToken, CloseDictToken, OpenArrayToken, CloseArrayToken,
    StringObject, NameObject, WordToken, NumberObject)


class TokenError(Exception):
    pass


class StreamWrapper(ABC):
    def __init__(self):
        self._prev = -1
        self._unget = False

    def __iter__(self):
        return self

    def __next__(self) -> int:
        if self._unget:
            self._unget = False
            return self._prev

        p = self._get()
        self._prev = p
        return self._prev

    @abstractmethod
    def _get(self) -> int:
        pass

    def unget(self):
        if self._prev == -1 or self._unget:
            return
        self._unget = True


class BinaryStreamWrapper(StreamWrapper):
    def __init__(self, stream: BinaryIO):
        StreamWrapper.__init__(self)
        self._stream = stream

    def _get(self) -> int:
        bytes_read = self._stream.read(1)
        if not bytes_read:
            raise StopIteration()

        return bytes_read[0]


def _bytes_to_string(cs):
    return struct.pack("{}B".format(len(cs)), *cs)


DELIMITERS = b"()<>[]{}/%"
WHITESPACES = b"\x00\t\n\x0c\r "
BACKSPACE = 0X08
FORM_FEED = 0X0C
LINE_FEED = 0X0A
CARRIAGE_RETURN = 0X0D
HORIZONTAL_TAB = 0X09
DOT = 0x2E
BACKSLASH = 0x5C
PERCENT_SIGN = 0x25
LEFT_PARENTHESIS = 0x28
RIGHT_PARENTHESIS = 0x29
ZERO_DIGIT = 0x30
NINE_DIGIT = 0x39
SLASH = 0x2F
LESS_THAN = 0x3C
GREATER_THAN = 0x3E
LEFT_SQUARE_BRACKET = 0x5B
RIGHT_SQUARE_BRACKET = 0x5D
A_UPPER = 0x41
Z_UPPER = 0x5A
A_LOWER = 0x61
B_LOWER = 0x62
F_LOWER = 0x66
N_LOWER = 0x6E
R_LOWER = 0x72
T_LOWER = 0x74
Z_LOWER = 0x7A
STAR = 0x2A

# Tokens and objects


XrefEntry = NamedTuple("XrefEntry", [
    ("byte_offset", bytes), ("gen_number", bytes),
    ("kw", bytes)
])


class State(ABC):
    @abstractmethod
    def handle(self, tokenizer: "PDFTokenizer", c: int):
        pass


class StartState(State):
    def handle(self, tokenizer: "PDFTokenizer", c: int):
        if c == SLASH:  # 3.2.4 Name Object
            tokenizer.set_state(NameObjectState())
        elif c == LESS_THAN:  # dict or hex string
            tokenizer.set_state(OpenDictOrHexStringState())
        elif c == GREATER_THAN:  # dict or hex string
            tokenizer.set_state(CloseDictState())
        elif c == LEFT_SQUARE_BRACKET:  # array
            return OpenArrayToken
        elif c == RIGHT_SQUARE_BRACKET:  # array
            return CloseArrayToken
        elif c == LEFT_PARENTHESIS:  # string
            tokenizer.set_state(StringState())
        elif c == PERCENT_SIGN:  # comment
            tokenizer.set_state(CommentState())
        elif c in b"+-.0123456789":
            tokenizer.set_state(DigitState(c))
        elif c in b" \r\n":
            pass
        else:
            tokenizer.set_state(WordState(c))


class NameObjectState(State):
    def __init__(self):
        self._cs = [SLASH]

    def handle(self, tokenizer: "PDFTokenizer", c: int):
        # TODO: hash
        if c in DELIMITERS or c in WHITESPACES:
            ret = struct.pack("{}B".format(len(self._cs)), *self._cs)
            tokenizer.unget()
            tokenizer.set_state(StartState())
            return NameObject(ret)
        else:
            self._cs.append(c)


class OpenDictOrHexStringState(State):
    def handle(self, tokenizer: "PDFTokenizer", c: int):
        if c == LESS_THAN:
            tokenizer.set_state(StartState())
            return OpenDictToken
        elif c in b"0123456789ABCDEFabcdef":  # 3.2.3 StringObject Objects
            tokenizer.set_state(HexStringState(c))
        elif c == GREATER_THAN:
            ret = b""
            tokenizer.set_state(StartState())
            return StringObject(ret)
        else:
            raise TokenError()


class CloseDictState(State):
    def handle(self, tokenizer: "PDFTokenizer", c: int):
        if c == GREATER_THAN:
            tokenizer.set_state(StartState())
            return CloseDictToken
        else:
            raise TokenError()


class StringState(State):
    def __init__(self):
        self._cs = []
        self._esc = False
        self._esc_cr = False
        self._lparen_count = 0
        self._ddd = None

    def handle(self, tokenizer: "PDFTokenizer", c: int):
        # TODO \ddd
        if self._ddd:
            if len(self._ddd) == 1:
                if ZERO_DIGIT <= c <= NINE_DIGIT:
                    self._ddd.append(c - ZERO_DIGIT)
                else:
                    self._cs.append(self._ddd[0])
                    self._ddd = None
                    tokenizer.unget()
            elif len(self._ddd) == 2:
                if ZERO_DIGIT <= c <= NINE_DIGIT:
                    self._ddd.append(c - ZERO_DIGIT)
                else:
                    self._cs.append(self._ddd[0] * 8 + self._ddd[1])
                    self._ddd = None
                    tokenizer.unget()
            elif len(self._ddd) == 3:
                self._cs.append(
                    self._ddd[0] * 64 + self._ddd[1] * 8 + self._ddd[2])
                self._ddd = None
                tokenizer.unget()
            ret = False
        elif self._esc:
            self._handle_esc(c)
            ret = False
        elif self._esc_cr:
            if c == LINE_FEED:
                self._esc_cr = False
                ret = False
            else:
                ret = self._handle_char(c)
        else:
            ret = self._handle_char(c)

        if ret:
            tokenizer.set_state(StartState())
            return StringObject(_bytes_to_string(self._cs))
        else:
            return None

    def _handle_esc(self, c):
        if c == B_LOWER:
            self._cs.append(BACKSPACE)
        elif c == F_LOWER:
            self._cs.append(FORM_FEED)
        elif c == N_LOWER:
            self._cs.append(LINE_FEED)
        elif c == R_LOWER:
            self._cs.append(CARRIAGE_RETURN)
        elif c == T_LOWER:
            self._cs.append(HORIZONTAL_TAB)
        elif c == LEFT_PARENTHESIS:
            self._cs.append(LEFT_PARENTHESIS)
        elif c == RIGHT_PARENTHESIS:
            self._cs.append(RIGHT_PARENTHESIS)
        elif c == BACKSLASH:
            self._cs.append(BACKSLASH)
        elif c == CARRIAGE_RETURN:
            self._esc_cr = True
        elif c == LINE_FEED:
            pass
        elif ZERO_DIGIT <= c <= NINE_DIGIT:
            self._ddd = [c - ZERO_DIGIT]
        else:
            self._cs.append(BACKSLASH)
            self._cs.append(c)
        self._esc = False

    def _handle_char(self, c: int) -> bool:
        if c == LEFT_PARENTHESIS:
            self._lparen_count += 1
            self._cs.append(c)
        elif c == RIGHT_PARENTHESIS:
            self._lparen_count -= 1
            if self._lparen_count < 0:
                return True
            else:
                self._cs.append(c)
        elif c == BACKSLASH:
            self._esc = True
        else:
            self._cs.append(c)
        return False


class CommentState(State):
    def __init__(self):
        self._cr = False

    def handle(self, tokenizer: "PDFTokenizer", c: int):
        if c == CARRIAGE_RETURN:
            self._cr = True
        elif c == LINE_FEED:
            tokenizer.set_state(StartState())
        elif self._cr:
            tokenizer.unget()
            tokenizer.set_state(StartState())


class DigitState(State):
    def __init__(self, c):
        self._cs = [c]
        self._dot = c == DOT

    def handle(self, tokenizer: "PDFTokenizer", c: int):
        if c == DOT:
            if self._dot:
                tokenizer.set_state(DigitState(c))
                return NumberObject(_bytes_to_string(self._cs))
            else:
                self._dot = True
                self._cs.append(c)
        elif c in b"0123456789":
            self._cs.append(c)
        else:
            tokenizer.unget()
            tokenizer.set_state(StartState())
            return NumberObject(_bytes_to_string(self._cs))


class WordState(State):
    def __init__(self, c):
        self._cs = [c]

    def handle(self, tokenizer: "PDFTokenizer", c: int):
        if A_LOWER <= c <= Z_LOWER or A_UPPER <= c <= Z_UPPER or c == STAR:
            self._cs.append(c)
        else:
            tokenizer.unget()
            tokenizer.set_state(StartState())
            return WordToken(_bytes_to_string(self._cs))


class HexStringState(State):
    def __init__(self, c):
        self._cs = [c]

    def handle(self, tokenizer: "PDFTokenizer", c: int):
        if c in b"0123456789ABCDEFabcdef":  # 3.2.3 StringObject Objects
            self._cs.append(c)
        elif c == GREATER_THAN:
            hex_string = _bytes_to_string(self._cs)
            if len(self._cs) % 2 == 1:
                hex_string += b"0"
            ret = bytes.fromhex(hex_string.decode("ascii"))
            tokenizer.set_state(StartState())
            return StringObject(ret)
        else:
            raise TokenError()


class PDFTokenizer:
    """Tokenizer for an obj"""

    @staticmethod
    def create(stream: BinaryIO) -> "PDFTokenizer":
        return PDFTokenizer(BinaryStreamWrapper(stream))

    def __init__(self, stream_wrapper: StreamWrapper):
        self._stream_wrapper = stream_wrapper
        self._state = cast(State, StartState())

    def set_state(self, state: State):
        self._state = state

    def __iter__(self) -> Iterator[Any]:
        for c in self._stream_wrapper:
            ret = self._state.handle(self, c)
            if ret is not None:
                yield ret

    def unget(self):
        self._stream_wrapper.unget()

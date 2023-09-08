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
import logging
import typing
from typing import NamedTuple, List, Any, Dict, Union, TypeVar, Type, cast


class _OpenDictTokenClass:
    def __repr__(self):
        return "OpenDictToken"


class _CloseDictTokenClass:
    def __repr__(self):
        return "CloseDictToken"


class _OpenArrayTokenClass:
    def __repr__(self):
        return "OpenArrayToken"


class _CloseArrayTokenClass:
    def __repr__(self):
        return "CloseArrayToken"


OpenDictToken = _OpenDictTokenClass()
CloseDictToken = _CloseDictTokenClass()
OpenArrayToken = _OpenArrayTokenClass()
CloseArrayToken = _CloseArrayTokenClass()


class StringObject:
    def __init__(self, bs: bytes):
        self.bs = bs

    def __repr__(self) -> str:
        return "StringObject({})".format(self.bs)


class NameObject:
    def __init__(self, bs: bytes):
        self.bs = bs

    def __repr__(self) -> str:
        return "NameObject({})".format(self.bs)


class WordToken:
    def __init__(self, bs: bytes):
        self.bs = bs

    def __repr__(self) -> str:
        return "WordToken({})".format(self.bs)


class ArrayObject:
    def __init__(self, arr: List[Any]):
        self._arr = arr

    def __repr__(self) -> str:
        return "ArrayObject(arr={})".format(self._arr)

    def __iter__(self):
        return self._arr.__iter__()


class DictObject:
    def __init__(self, d: Dict[bytes, "PDFObject"]):
        self._d = d

    def __repr__(self) -> str:
        return "DictObject(obj={})".format(repr(self._d))

    def __getitem__(self, item: bytes) -> "PDFObject":
        return self._d.__getitem__(item)

    def __contains__(self, item: bytes) -> bool:
        return self._d.__contains__(item)

    def get(self, item: bytes, default_value=None) -> "PDFObject":
        return self._d.get(item, default_value)

    def items(self) -> typing.ItemsView[bytes, "PDFObject"]:
        return self._d.items()


BooleanObject = NamedTuple("BooleanObject", [("value", bool)])


class NullObject: pass


null_object_instance = NullObject()


class NumberObject:
    def __init__(self, bs: bytes):
        self._bs = bs

    def __repr__(self) -> str:
        return "NumberObject(text={})".format(repr(self._bs))

    @property
    def value(self) -> Union[int, float]:
        if b"." in self._bs:
            return float(self._bs)
        else:
            return int(self._bs)


class IndirectRef:
    def __init__(self, obj_num: NumberObject, gen_num: NumberObject):
        self._obj_num = obj_num
        self._gen_num = gen_num

    def __repr__(self) -> str:
        return "IndirectRef(obj_num={}, gen_num={})".format(self._obj_num,
                                                            self._gen_num)

    @property
    def obj_num(self) -> int:
        return self._obj_num.value

    @property
    def gen_num(self) -> int:
        return self._gen_num.value


class IndirectObject:
    def __init__(self, obj_num: int, gen_num: int, object: Any):
        self.obj_num = obj_num
        self.gen_num = gen_num
        self.object = object

    def __repr__(self) -> str:
        return "IndirectObject({}, {}, {})".format(
            self.obj_num, self.gen_num, self.object)


class StreamObject:
    def __init__(self, obj_num: int, gen_num: int, object: DictObject,
                 start: int, length: int):
        self.obj_num = obj_num
        self.gen_num = gen_num
        self.object = object
        self.start = start
        self.length = length

    def __repr__(self, ):
        return "StreamObject({}, {}, {}, {}, {})".format(self.obj_num,
                                                         self.gen_num,
                                                         self.object,
                                                         self.start,
                                                         self.length)


def get_num(dict_object: DictObject, key: bytes,
            default_value: Union[int, float] = None) -> Union[int, float]:
    try:
        value = checked_cast(NumberObject, dict_object[key]).value
    except KeyError:
        if default_value is None:
            raise
        value = default_value
    return value


def get_string(dict_object: DictObject, key: bytes,
               default_value: bytes = None) -> bytes:
    try:
        value = checked_cast(StringObject, dict_object[key]).bs
    except KeyError:
        if default_value is None:
            raise
        value = default_value
    return value


def check(value: bool, format_string: str, *parameters):
    if not value:
        raise Exception(format_string.format(*parameters))


T = TypeVar('T')


def checked_cast(typ: Type[T], val: Any) -> T:
    check(isinstance(val, typ), "Expected type {} for value {} ({})", typ, val,
          type(val))
    return cast(typ, val)


class TextMatrix:
    _logger = logging.getLogger(__name__)

    @staticmethod
    def identity() -> "TextMatrix":
        return TextMatrix(1, 0, 0, 1, 0, 0)

    def __init__(self, a, b, c, d, e, f):
        self.a = a
        self.b = b
        self.c = c
        self.d = d
        self.e = e
        self.f = f

    def __mul__(self, other: "TextMatrix") -> "TextMatrix":
        return TextMatrix(self.a * other.a + self.b * other.c,
                          self.a * other.b + self.b * other.d,
                          self.c * other.a + self.d * other.c,
                          self.c * other.b + self.d * other.d,
                          self.e * other.a + self.f * other.c + other.e,
                          self.e * other.b + self.f * other.d + other.f
                          )

    def shift(self, w: float, h: float):
        self.e += w * self.a + h * self.c
        self.f += w * self.b + h * self.d
        self._logger.debug(">> Shift > cur text matrix is: %s", self)

    def __repr__(self):
        return repr(
            [[self.a, self.b, 0], [self.c, self.d, 0], [self.e, self.f, 1]])

    def clone(self) -> "TextMatrix":
        return TextMatrix(self.a, self.b, self.c, self.d, self.e, self.f)


class TextElement:
    pass


class Text(TextElement):
    def __init__(self, s: str, x: float, y: float, width: float, height: float,
                 font_size: float, font_space_width: float):
        self.s = s
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.font_size = font_size
        self.font_space_width = font_space_width

    def __repr__(self):
        return "Text({}, x={}, y={}, w={}, h={}, fs={}, fw={})".format(
            repr(self.s), self.x, self.y, self.width, self.height,
            self.font_size, self.font_space_width)


class NewText(TextElement):
    pass


class NewPage(TextElement):
    pass

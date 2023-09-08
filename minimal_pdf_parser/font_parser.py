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
from typing import Mapping, cast, Dict, Any

from base import (checked_cast, DictObject, IndirectRef, NameObject,
                  ArrayObject,
                  NumberObject)
from content_parser import ContentParser
from pdf_encodings import STD_ENCODING, ENCODING_BY_NAME

Encoding = Mapping[int, str]
Widths = Mapping[int, float]

class Font:
    def __init__(self, encoding: Encoding, widths: Widths, missing_width: float):
        self.encoding = encoding
        self.widths = widths
        self.missing_width = missing_width

    def get_space_width(self) -> float:
        return self.get_char_width(" ")
    def get_char_width(self, c: str) -> float:
        return self.widths.get(ord(c), self.missing_width)

    def get_pos_width(self, i: int) -> float:
        return self.widths.get(i, self.missing_width)

    def is_space(self, i: int) -> bool:
        return self.encoding.get(i) == " "

    def __repr__(self):
        return "Font(encoding={}, widths={}, missing_width={}".format(self.encoding, self.widths, self.missing_width)


class FontParser:
    """
    Table 111 – Entries in a Type 1 font dictionary
    Table 121 – Entries in a Type 0 font dictionary
    """
    _logger = logging.getLogger(__name__)

    def __init__(self, document: "PDFDocument",
                 unicode_by_glyph_name: Mapping[bytes, str],
                 encoding_by_name: Mapping[str, Encoding]):
        self._document = document
        self._unicode_by_glyph_name = unicode_by_glyph_name
        self._encoding_by_name = encoding_by_name
        self._font_by_obj_num = cast(Dict[int, Font], {})
        self._font_by_name = {}

    def parse(self, v: Any) -> Font:
        font_object = checked_cast(DictObject, self._document.get_object(v))
        if isinstance(font_object, IndirectRef):
            obj_num = font_object.obj_num
            try:
                return self._font_by_obj_num[obj_num]
            except KeyError:
                font_object = self._document.deref_object(font_object)
                font = self.parse_font_object(font_object)
                self._font_by_obj_num[obj_num] = font
                return font
        else:
            return self.parse_font_object(font_object)

    def parse_font_object(self,
                          font_object: DictObject) -> Font:
        subtype = self._get_subtype(font_object)
        # Table 122 – Entries common to all font descriptors
        # missing_width = self._get_missing_width(font_object)
        self._logger.debug("Font type %s", subtype)

        # Table 110 – Font types
        if subtype == b"/Type0":
            font = self._parse_type0_font(font_object)
        elif subtype == b"/Type1":
            font = self._parse_type1_font(font_object)
        elif subtype == b"/MMType1":
            raise NotImplementedError(subtype)
        elif subtype == b"/Type3":
            raise NotImplementedError(subtype)
        elif subtype == b"/TrueType":
            font = self._parse_truetype_font(font_object)
        elif subtype == b"/CIDFontType0":
            raise NotImplementedError(subtype)
        elif subtype == b"/CIDFontType2":
            raise NotImplementedError(subtype)
        else:
            raise ValueError(subtype)
        return font

    def _get_subtype(self, obj: DictObject) -> bytes:
        try:
            subtype_object = self._document.get_object(obj[b"/Subtype"])
        except KeyError:
            raise
        else:
            return cast(NameObject, subtype_object).bs

    def _parse_type0_font(self, font_object: DictObject) -> Font:
        """ 9.7 Composite Fonts
        Table 121 – Entries in a Type 0 font dictionary
        """
        encoding = self._parse_type0_encoding(font_object)
        widths = {} # TODO
        missing_width = 0.0
        return Font(encoding, widths, missing_width)

    def _parse_type0_encoding(self, font_object: DictObject) -> Encoding:
        try:
            encoding_object_or_ref = font_object[b"/Encoding"]
        except KeyError:
            return STD_ENCODING
        else:
            encoding_object = self._document.get_object(encoding_object_or_ref)
            if isinstance(encoding_object, NameObject):
                encoding_name = cast(NameObject, encoding_object).bs
                try:
                    encoding = ENCODING_BY_NAME[encoding_name]
                    return encoding
                except KeyError:
                    try:
                        to_unicode_stream_wrapper = self._document.get_stream(
                            font_object[b"/ToUnicode"])
                    except KeyError:
                        raise
                    else:
                        # 9.10.3 ToUnicode CMaps
                        encoding = ContentParser().parse_to_unicode(
                            to_unicode_stream_wrapper)
                        self._logger.info("To Unicode: %s", encoding)
                        return encoding  # TODO apply to base encoding
            elif isinstance(encoding_object, DictObject):
                base_encoding = self._get_base1_encoding(encoding_object)
                return self._apply_differences(encoding_object, base_encoding)
            else:
                raise ValueError()

    def _check_type(self, encoding_object: DictObject):
        try:
            type_object = self._document.get_object(encoding_object[b"/Type"])
        except KeyError:
            pass
        else:
            type_name = cast(NameObject, type_object).bs
            if type_name != b"/Encoding":
                self._logger.warning("Expected /Encoding, was %s", type_name)

    def _parse_type1_font(self, font_object: DictObject) -> Font:
        self._logger.debug("Parse Type 1 Font: %s", font_object)
        encoding = self._parse_type1_encoding(font_object)
        widths = self._parse_widths(font_object)
        missing_width = self._get_missing_width(font_object)
        return Font(encoding, widths, missing_width)

    def _parse_type1_encoding(self, font_object: DictObject) -> Encoding:
        """
        9.6.2 Type 1 Fonts
        """
        try:
            encoding_object = self._document.get_object(
                font_object[b"/Encoding"])
        except KeyError:
            # try with b"/ToUnicode"
            return STD_ENCODING
        else:
            self._logger.debug("Parse Type 1 Font Encoding: %s", encoding_object)
            if isinstance(encoding_object, NameObject):
                encoding_name = cast(NameObject, encoding_object).bs
                encoding = ENCODING_BY_NAME.get(encoding_name, [])
                return encoding
            elif isinstance(encoding_object, DictObject):
                base_encoding = self._get_base1_encoding(encoding_object)
                self._logger.debug("Base Encoding is: %s",
                                   base_encoding)
                return self._apply_differences(encoding_object, base_encoding)
            else:
                raise ValueError()

    # BaseFont

    def _get_base1_encoding(self, encoding_object) -> Encoding:
        encoding_object = cast(DictObject, encoding_object)
        self._check_type(encoding_object)
        try:
            base_encoding_object = self._document.get_object(
                encoding_object[b"/BaseEncoding"])
        except KeyError:
            # TODO: get_object(/Encoding)
            base_encoding = STD_ENCODING
        else:
            base_encoding_name = cast(NameObject, base_encoding_object).bs
            base_encoding = ENCODING_BY_NAME.get(base_encoding_name, [])
        return base_encoding

    def _parse_truetype_font(self, font_object: DictObject) -> Font:
        """
        9.6.3 TrueType Fonts
        """
        self._logger.debug("Parse TrueType Font: %s", font_object)
        encoding = self._parse_truetype_encoding(font_object)
        widths = self._parse_widths(font_object)
        missing_width = self._get_missing_width(font_object)
        return Font(encoding, widths, missing_width)

    def _parse_truetype_encoding(self, font_object: DictObject) -> Encoding:
        try:
            encoding_object = self._document.get_object(
                font_object[b"/Encoding"])
        except KeyError:
            # try with b"/ToUnicode"
            return STD_ENCODING
        else:
            if isinstance(encoding_object, NameObject):
                encoding_name = cast(NameObject, encoding_object).bs
                encoding = ENCODING_BY_NAME.get(encoding_name, [])
                return encoding
            elif isinstance(encoding_object, DictObject):
                base_encoding = self._get_base1_encoding(encoding_object)
                self._logger.error("TODO enc %s", base_encoding)  # TODO
            else:
                raise ValueError()

    def _apply_differences(self, encoding_object: DictObject,
                           base_encoding: Encoding) -> Encoding:
        try:
            differences = self._document.get_object(
                encoding_object[b"/Differences"])
        except KeyError:
            return base_encoding
        else:
            encoding = dict(base_encoding)
            differences_array = cast(ArrayObject, differences)
            i = 0
            for element in differences_array:
                if isinstance(element, NumberObject):
                    i = element.value
                elif isinstance(element, NameObject):
                    element_name = element.bs
                    self._logger.debug("Diff: %s %s",
                                       i, element_name)
                    encoding[i] = self._unicode_by_glyph_name.get(
                        element_name, '\ufffd')
                    i += 1
                else:
                    raise ValueError()
            return encoding

    def _parse_widths(self, font_object: DictObject) -> Mapping[int, float]:
        """
        Table 111 – Entries in a Type 1 font dictionary
        Table 112 – Entries in a Type 3 font dictionary

        :param font_object:
        :return:
        """
        try:
            first_char = cast(NumberObject, font_object[b"/FirstChar"]).value
            last_char = cast(NumberObject, font_object[b"/LastChar"]).value
            widths = cast(ArrayObject, self._document.get_object(font_object[b"/Widths"]))
        except KeyError:
            return {}
        else:
            return {i: checked_cast(NumberObject, no).value for i, no in zip(range(first_char, last_char + 1), widths)}

    def _get_missing_width(self, font_object: DictObject) -> float:
        try:
            return checked_cast(NumberObject, font_object[b"/MissingWidth"]).value
        except KeyError:
            return 0.0

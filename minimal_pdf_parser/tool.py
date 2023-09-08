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
import io
import logging
from typing import Iterator, Iterable, List, Optional, TextIO

from base import TextElement, NewPage, NewText, Text
from content_parser import ContentParser
from font_parser import Font
from parser import PDFDocument, TextState, PDFObject
from pdf_encodings import STD_ENCODING
from pdf_operation import (
    SetFont, SetTextRise, SetHorizScaling, SetCharSpacing,
    SetWordSpacing, ShowTextString, MoveStartNextLine, SetTextMatrix,
    UpdateTextMatrix, MoveStartNextLineWoParams, SetTextLeading
)


class TextExtractorParameters:
    def __init__(self):
        pass

    def is_other_line(self, delta_y: float, font_size: float) -> bool:
        return abs(delta_y) > font_size

    def take(self, page_count: int) -> bool:
        return True  # page_count == 258


class TextExtractor:
    _logger = logging.getLogger(__name__)

    def __init__(self, document: PDFDocument,
                 parameters: TextExtractorParameters = None):
        self.document = document
        if parameters is None:
            self._parameters = TextExtractorParameters()
        else:
            self._parameters = parameters
        self.text_state = TextState()

    def execute(self) -> Iterator[TextElement]:
        for page_count, page_object in enumerate(self.document.get_pages()):
            if self._parameters.take(page_count):
                self._logger.debug("Page %s", page_count + 1)
                yield from self._execute_page(page_count, page_object)

    def _execute_page(self, page_count: int,
                      page_object: PDFObject) -> Iterator[TextElement]:
        yield NewPage()
        self._logger.debug("Process page: %s (%s)", page_object, page_count)
        # kid is a page
        self.document.handle_fonts(page_object)
        contents = page_object[b"/Contents"]
        self._logger.debug("Contents: %s",
                           self.document.get_object(contents))
        stream_wrapper = self.document.get_stream(contents)
        font = Font(STD_ENCODING, {}, 0.0)
        encoding = STD_ENCODING
        for x in ContentParser().parse_content(stream_wrapper):
            # TODO : if space more than one em (space width), new block
            if isinstance(x, SetFont):  # Tf
                self._logger.debug("SetFont %s", x.name)
                font = self.document.get_font(x.name)
                encoding = font.encoding
                self.text_state.text_font_size = x.size
            elif isinstance(x, SetTextRise):  # Ts
                self._logger.debug("SetTextRise %s", x.rise)
                self.text_state.text_rise = x.rise
            elif isinstance(x, SetHorizScaling):  # Tz
                self._logger.debug("SetHorizScaling %s", x.scale)
                self.text_state.horizontal_scaling = x.scale
            elif isinstance(x, SetCharSpacing):  # Tc
                self._logger.debug("SetCharSpacing %s", x.char_space)
                self.text_state.char_space = x.char_space
            elif isinstance(x, SetWordSpacing):  # Tw
                self._logger.debug("SetWordSpacing %s", x.word_space)
                self.text_state.word_space = x.word_space
            elif isinstance(x, ShowTextString):  # Tj
                bs = x.bs
                try:
                    text = "".join(
                        encoding.get(y, '\ufffd')
                        for y in bs if y
                    )  # todo : TWO BYTES, EG. "� " = " "
                    self._logger.info("Bytes %s -> %s", repr(bs), repr(text))
                    x = self.text_state.x
                    y = self.text_state.y
                    font_size = self.text_state.font_size
                    w = self._get_width(font, bs, font_size)
                    font_space_width = font.get_space_width()

                    # between chars: change text now
                    cs = 1000 * self.text_state.char_space
                    if 0 < font_space_width < cs:
                        factor = int(cs / font_space_width)
                        text = (" " * factor).join(list(text))

                    # newline
                    delta_y = 0 if self.text_state.last_y is None else y - self.text_state.last_y
                    self._logger.debug("Delta Y: %s", delta_y)
                    if self._parameters.is_other_line(delta_y, font_size):
                        yield NewText()
                        # text = "\n" + text
                    else:
                        # before
                        delta_x = 0 if self.text_state.last_x is None else x - self.text_state.last_x
                        self._logger.debug("Delta X: %s", delta_x)
                        if font_size:
                            temp = (delta_x * 1000) / font_size
                            if 0 < font_space_width < temp:
                                yield NewText()
                                factor = int(temp / font_space_width)
                                # text = (" " * factor) + text

                    self.text_state.shift_left_tm(w / 1000)
                    width = self.text_state.x - x
                    t = Text(text, x, y, width, 0.0, font_size,
                             font_space_width)
                    self._logger.info("Text => %s (y=%s)", t, y)
                    # 9.2.4 Glyph Positioning and Metrics
                    self.text_state.store_xy()
                    yield t
                except (IndexError, KeyError):
                    self._logger.exception("%s %s", repr(bs),
                                           encoding)
            elif isinstance(x, MoveStartNextLine):  # Td
                font_size = self.text_state.font_size
                if self._parameters.is_other_line(x.ty, font_size):
                    self._logger.debug("Newline %s", x)
                else:
                    self._logger.debug("Ignore Newline %s", x)
                self.text_state.move_new_line(x.tx, x.ty)
            elif isinstance(x, SetTextMatrix):  # Tm
                self._logger.debug("SetTextMatrix %s", x)
                self.text_state.set_text_matrix(x.tm)
            elif isinstance(x, UpdateTextMatrix):  # TJ part
                self._logger.debug("UpdateTextMatrix %s", x)
                # 9.4.4 Text Space Details
                self.text_state.shift_left_tm(-x.w / 1000)
            elif isinstance(x, MoveStartNextLineWoParams):  # T*
                self._logger.debug("Ignore Newline WO Params %s", x)
                self.text_state.move_new_line(0, -self.text_state.text_leading)
            elif isinstance(x, SetTextLeading):  # TL
                self._logger.debug("SetTextLeading %s", x.leading)
                self.text_state.text_leading = x.leading
            else:
                self._logger.debug("*Ignore %s", x)

    def _get_width(self, font: Font, bs: bytes, a):
        """9.4.4 Text Space Details"""
        space_count = sum(1 for i in bs if i == 32)
        return (sum(
            font.get_pos_width(i)
            for i in bs
        ) + self.text_state.char_space * (len(bs) - 1) * 1000
                + self.text_state.word_space * space_count * 1000) * (
                self.text_state.horizontal_scaling / 100.0)


class TextProcessor:
    def process_texts(self, d: io.StringIO, texts: Iterable[TextElement]):
        cur_txt = None
        txts = []
        for text in texts:
            if isinstance(text, Text):
                if cur_txt is None:
                    cur_txt = text
                else:
                    cur_txt.s += text.s
                    cur_txt.width = text.x + text.width - cur_txt.x
            elif isinstance(text, NewText):
                if cur_txt is not None:
                    txts.append(cur_txt)
                    cur_txt = None
            elif isinstance(text, NewPage):
                if cur_txt is not None:
                    txts.append(cur_txt)

                if txts:
                    self.merge_texts(d, txts)
                cur_txt = None
                txts = []

    def merge_texts(self, d: io.StringIO, txts: List[Text]):
        from statistics import mode

        font_size = mode(t.font_size for t in txts)
        if font_size == 0:
            font_size = min([
                t.font_size
                for t in txts
                if t.font_size > 0
            ], default=10)
        font_space_width = mode(
            t.font_space_width * t.font_size for t in txts) / 1000
        if font_space_width == 0:
            font_space_width = min([
                t.font_space_width * t.font_size
                for t in txts
                if t.font_space_width * t.font_size > 0
            ], default=10)

        last_cx = 0
        last_cy = 0
        last_ty = 0
        for t in sorted(txts, key=lambda t: (-t.y, t.x)):
            if isinstance(t, Text):
                cy = int(t.y / font_size)
                factor_y = (last_cy - cy)
                if factor_y > 1 and (last_ty - t.y) < 1.5 * font_size:
                    factor_y = 1

                last_cy = cy
                last_ty = t.y

                cx = int(t.x / font_space_width)
                if factor_y != 0:  # new line
                    last_cx = 0
                factor_x = cx - last_cx
                if factor_y > 0:
                    d.write("\n" * factor_y)
                if factor_x > 0:
                    d.write(" " * factor_x)
                    last_cx = cx + len(t.s)

                d.write(t.s)
        d.write("\n>>>>>>>>>>>>>>>>\n")

class AlternativeTextProcessor(TextProcessor):
    def merge_texts(self, d, txts: List[Text]):
        last_x = 0
        last_y = 0
        for t in sorted(txts, key=lambda t: (-t.y, t.x)):
            if isinstance(t, Text):
                if last_y is not None:
                    delta_y = last_y - t.y
                    if delta_y > t.font_size > 0:
                        factor = int(delta_y / t.font_size)
                        d.write("\n" * factor)
                        new_line = True
                        last_x = 0  # None

                    if last_x is not None:
                        delta_x = t.x - last_x
                        if t.font_size > 0:
                            temp = (delta_x * 1000) / t.font_size
                            if 0 < t.font_space_width < temp:
                                factor = int(
                                    temp / t.font_space_width)
                                d.write(" " * factor)

                d.write(t.s)
                last_x = t.x + t.width
                last_y = t.y
        d.write("\n>>>>>>>>>>>>>>>>\n")


class RawTextProcessor(TextProcessor):
    def merge_texts(self, d, txts: List[Text]):
        for t in txts:
            if isinstance(t, Text):
                d.write(t.s + "\n")
        d.write("\n>>>>>>>>>>>>>>>>\n")


def extract_text(
        document: PDFDocument,
        text_processor: TextProcessor, d: TextIO,
        parameters: Optional["TextExtractorParameters"] = None
):
    text_processor.process_texts(d, iter_texts(document, parameters))


def iter_texts(
        document: PDFDocument,
        parameters: Optional["TextExtractorParameters"] = None
) -> Iterator[TextElement]:
    document.prepare_decryption()
    yield from TextExtractor(document, parameters).execute()

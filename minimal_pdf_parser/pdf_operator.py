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
from typing import Any, List

from base import checked_cast, NumberObject, StringObject, OpenArrayToken, \
    CloseArrayToken, NameObject, TextMatrix
from pdf_operation import *
from pdf_operation import StrokePath, SetWordSpacing, SetCharSpacing, \
    UpdateTextMatrix, SetTextRise


class TokenQueue:
    _logger = logging.getLogger(__name__)

    def __init__(self):
        self._arr = []

    def push(self, element: Any):
        self._arr.append(element)

    def ignore(self):
        if self._arr:
            self._logger.warning("queue err: %s (empty)", self._arr)
            self.clear()

    def shift(self) -> Any:
        if not self._arr:
            self._logger.warning("queue err: %s (empty)", self._arr)
            return None

        return self._arr.pop(0)

    def shift_arr(self) -> List[Any]:
        token = self.shift()
        if token is not OpenArrayToken:
            self._logger.warning("Expected open array, was: %s", token)
        ret = []
        token = self.shift()
        while token and token is not CloseArrayToken:
            ret.append(token)
            token = self.shift()
        return ret

    def shift_n(self, n: int = 1) -> List[Any]:
        if len(self._arr) == n:
            ret = self._arr[:]
        elif len(self._arr) < n:
            self._logger.warning("queue err: %s (%s)", self._arr, n)
            ret = self._arr + [None] * (n - len(self._arr))
        else:  # len(queue: TokenQueue) > n:
            self._logger.warning("queue err: %s (%s)", self._arr, n)
            ret = self._arr[:n]

        assert len(ret) == n
        self.clear()
        return ret

    def clear(self):
        self._arr.clear()


class Operator:
    def build(self, queue: TokenQueue) -> List[Operation]:
        """Ignore operator or override this method !"""
        queue.clear()
        return []


# Table 57 – Graphics State Operators

class SaveCurGraphicsStateOperator(Operator):
    def build(self, queue: TokenQueue) -> List[Operation]:
        queue.ignore()
        return [SaveCurGraphicsState()]


class RestoreCurGraphicsStateOperator(Operator):
    def build(self, queue: TokenQueue) -> List[Operation]:
        queue.ignore()
        return [RestoreCurGraphicsState()]


class ModifyCTMOperator(Operator):
    def build(self, queue: TokenQueue) -> List[Operation]:
        a, b, c, d, e, f = [checked_cast(NumberObject, x).value for x in
                            queue.shift_n(6)]
        return [ModifyCTM(a, b, c, d, e, f)]


class SetLineWidthOperator(Operator):
    def build(self, queue: TokenQueue) -> List[Operation]:
        width = checked_cast(NumberObject, queue.shift()).value
        return [SetLineWidth(width)]


class SetLineCapOperator(Operator):
    def build(self, queue: TokenQueue) -> List[Operation]:
        cap = checked_cast(NumberObject, queue.shift()).value
        return [SetLineCap(cap)]


class SetLineJoinOperator(Operator):
    def build(self, queue: TokenQueue) -> List[Operation]:
        join = queue.shift()
        return [SetLineJoin(join)]


class SetMiterLimitOperator(Operator):
    def build(self, queue: TokenQueue) -> List[Operation]:
        miter_limit = queue.shift()
        return [SetMiterLimit(miter_limit)]


class SetLineDashPatternOperator(Operator):
    def build(self, queue: TokenQueue) -> List[Operation]:
        dash_array = queue.shift_arr()  # array of numbers
        dash_phase = queue.shift()  # number
        return [SetLineDashPattern(dash_array, dash_phase)]


class SetColourRenderingIntentOperator(Operator):
    def build(self, queue: TokenQueue) -> List[Operation]:
        intent = queue.shift()
        return [SetColourRenderingIntent(intent)]


class SetFlatnessToleranceOperator(Operator):
    def build(self, queue: TokenQueue) -> List[Operation]:
        flatness = queue.shift()
        return [SetFlatnessTolerance(flatness)]


class SetParametersOperator(Operator):
    def build(self, queue: TokenQueue) -> List[Operation]:
        dict_name = queue.shift()
        return [SetParameters(dict_name)]


# Table 59 – Path Construction Operators

class BeginSubpathOperator(Operator):
    def build(self, queue: TokenQueue) -> List[Operation]:
        x, y = queue.shift_n(2)
        return [BeginSubpath(x, y)]


class AppendStraightLineOperator(Operator):
    def build(self, queue: TokenQueue) -> List[Operation]:
        x, y = queue.shift_n(2)
        return [AppendStraightLine(x, y)]


class AppendCubicBezier1Operator(Operator):
    def build(self, queue: TokenQueue) -> List[Operation]:
        x1, y1, x2, y2, x3, y3 = queue.shift_n(6)
        return [AppendCubicBezier1(x1, y1, x2, y2, x3, y3)]


class AppendCubicBezier2Operator(Operator):
    def build(self, queue: TokenQueue) -> List[Operation]:
        x2, y2, x3, y3 = queue.shift_n(4)
        return [AppendCubicBezier2(x2, y2, x3, y3)]


class AppendCubicBezier3Operator(Operator):
    def build(self, queue: TokenQueue) -> List[Operation]:
        x1, y1, x3, y3 = queue.shift_n(4)
        return [AppendCubicBezier3(x1, y1, x3, y3)]


class ClosePathOperator(Operator):
    def build(self, queue: TokenQueue) -> List[Operation]:
        queue.ignore()
        return [ClosePath()]


class AppendRectangleOperator(Operator):
    def build(self, queue: TokenQueue) -> List[Operation]:
        x, y, w, h = queue.shift_n(4)
        return [AppendRectangle(x, y, w, h)]


# Table 60 – Path-Painting Operators

class StrokePathOperator(Operator):
    def build(self, queue: TokenQueue) -> List[Operation]:
        queue.ignore()
        return [StrokePath()]


class CloseAndStrokePathOperator(Operator):
    def build(self, queue: TokenQueue) -> List[Operation]:
        queue.ignore()
        return [ClosePath(), StrokePath()]


class FillPathNZWOperator(
    Operator):  # Equivalent to f; included only for compatibility
    pass


class FillPathOEROperator(Operator):
    pass


class FillAndStrokePathNZWOperator(Operator):
    pass


class FillAndStrokePathOEROperator(Operator):
    pass


class CloseFillAndStrokePathNZWOperator(Operator):
    pass


class CloseFillAndStrokePathOEROperator(Operator):
    pass


class EndPathOperator(Operator):
    pass


# Table 61 – Clipping Path Operators

class IntersectNZWOperator(Operator):
    pass


class IntersectOEROperator(Operator):
    pass


# Table 107 – Text object operators

class BeginTextOperator(Operator):
    def build(self, queue: TokenQueue) -> List[Operation]:
        queue.ignore()
        return [BeginText()]


class EndTextOperator(Operator):
    def build(self, queue: TokenQueue) -> List[Operation]:
        queue.ignore()
        return [EndText()]


# Table 108 – Text-positioning operators

class MoveStartNextLineOperator(Operator):
    def build(self, queue: TokenQueue) -> List[Operation]:
        tx, ty = [checked_cast(NumberObject, x).value for x in queue.shift_n(2)]
        return [MoveStartNextLine(tx, ty)]


class MoveStartNextLineTextStateOperator(Operator):
    def build(self, queue: TokenQueue) -> List[Operation]:
        tx, ty = [checked_cast(NumberObject, x).value for x in queue.shift_n(2)]
        return [SetTextLeading(-ty), MoveStartNextLine(tx, ty)]


class SetTextMatrixOperator(Operator):
    def build(self, queue: TokenQueue) -> List[Operation]:
        a, b, c, d, e, f = [checked_cast(NumberObject, x).value for x in
                            queue.shift_n(6)]
        return [SetTextMatrix(TextMatrix(a, b, c, d, e, f))]


class MoveStartNextLineWoParamsOperator(Operator):
    def build(self, queue: TokenQueue) -> List[Operation]:
        queue.ignore()
        return [MoveStartNextLineWoParams()]


# Table 109 – Text-showing operators

class ShowTextStringOperator(Operator):
    def build(self, queue: TokenQueue) -> List[Operation]:
        bs = checked_cast(StringObject, queue.shift()).bs
        return [ShowTextString(bs)]


class MoveStartNextLineAndShowTextStringOperator(Operator):
    def build(self, queue: TokenQueue) -> List[Operation]:
        bs = checked_cast(StringObject, queue.shift()).bs
        return [MoveStartNextLineWoParams(), ShowTextString(bs)]


class MoveStartNextLineAndShowTextStringWWordSpacingOperator(Operator):
    """ " """

    def build(self, queue: TokenQueue) -> List[Operation]:
        aw = checked_cast(NumberObject, queue.shift()).value
        ac = checked_cast(NumberObject, queue.shift()).value
        string = checked_cast(StringObject, queue.shift()).bs
        logging.getLogger().warning("%s, %s", self, queue)
        return [SetWordSpacing(aw), SetCharSpacing(ac),
                MoveStartNextLineWoParams(), ShowTextString(string)]


class ShowTextStringsOperator(Operator):
    _logger = logging.getLogger(__name__)

    def build(self, queue: TokenQueue) -> List[Operation]:
        arr = queue.shift_arr()
        ret = []
        for token in arr:
            if isinstance(token, StringObject):
                ret.append(ShowTextString(token.bs))
            elif isinstance(token, NumberObject):
                ret.append(UpdateTextMatrix(token.value))
            else:
                self._logger.warning("Unexpected TD array token %s", token)

        return ret


# Table 113 – Type 3 font operators

class SetGlyphWidthOperator(Operator):
    pass


class SetGlyphBBOperator(Operator):
    pass


# Table 74 – Colour Operators

class SetCurColourSpace1Operator(Operator):
    pass


class SetCurColourSpace1NonStrokingOperator(Operator):
    pass


class SetCurColourSpace2Operator(Operator):
    pass


class SetCurColourSpace3Operator(Operator):
    pass


class SetCurColourSpace2NonStrokingOperator(Operator):
    pass


class SetCurColourSpace3NonStrokingOperator(Operator):
    pass


class SetStrokingColourSpaceToGrayOperator(Operator):
    pass


class SetStrokingColourSpaceToGrayNonStrokingOperator(Operator):
    pass


class SetStrokingColourSpaceToRGBOperator(Operator):
    pass


class SetStrokingColourSpaceToRGBNonStrokingOperator(Operator):
    pass


class SetStrokingColourSpaceToCMYKOperator(Operator):
    pass


class SetStrokingColourSpaceToCMYKNonStrokingOperator(Operator):
    pass


# Table 77 – Shading Operator

class PaintShapeOperator(Operator):
    pass


# Table 92 – Inline Image Operators

class BeginInlineImageOperator(Operator):
    pass


class BeginInlineImageDataOperator(Operator):
    pass


class EndInlineImageOperator(Operator):
    pass


# Table 87 – XObject Operator

class PaintXObjectOperator(Operator):
    pass


# Table 320 – Marked-content operators

class MarkedContentOperator(Operator):
    pass


class MarkedContentWListOperator(Operator):
    pass


class BeginMarkedContentOperator(Operator):
    pass


class BeginMarkedContentWPropertiesOperator(Operator):
    pass


class EndMarkedContentOperator(Operator):
    pass


# Table 32 – Compatibility operators
class BeginCompatibilityOperator(Operator):
    pass


class EndCompatibilityOperator(Operator):
    pass


################################################
# Table 105 – Text state operators

class SetCharSpacingOperator(Operator):
    def build(self, queue: TokenQueue) -> List[Operation]:
        char_space = checked_cast(NumberObject, queue.shift()).value
        return [SetCharSpacing(char_space)]

    pass


class SetWordSpacingOperator(Operator):
    def build(self, queue: TokenQueue) -> List[Operation]:
        word_space = checked_cast(NumberObject, queue.shift()).value
        return [SetWordSpacing(word_space)]


class SetHorizScalingOperator(Operator):
    def build(self, queue: TokenQueue) -> List[Operation]:
        scale = checked_cast(NumberObject, queue.shift()).value
        return [SetHorizScaling(scale)]


class SetTextLeadingOperator(Operator):
    def build(self, queue: TokenQueue) -> List[Operation]:
        leading = checked_cast(NumberObject, queue.shift()).value
        return [SetTextLeading(leading)]


class SetFontOperator(Operator):
    def build(self, queue: TokenQueue) -> List[Operation]:
        font = checked_cast(NameObject, queue.shift()).bs
        size = checked_cast(NumberObject, queue.shift()).value
        return [SetFont(font, size)]


class SetTextRenderingModeOperator(Operator):
    pass


class SetTextRiseOperator(Operator):
    def build(self, queue: TokenQueue) -> List[Operation]:
        rise = checked_cast(NumberObject, queue.shift()).value
        return [SetTextRise(rise)]


operator_by_token_bytes = {
    # Table 57 – Graphics State Operators
    b"q": SaveCurGraphicsStateOperator(),
    b"Q": RestoreCurGraphicsStateOperator(),
    b"cm": ModifyCTMOperator(),
    b"w": SetLineWidthOperator(),
    b"J": SetLineCapOperator(),
    b"j": SetLineJoinOperator(),
    b"M": SetMiterLimitOperator(),
    b"d": SetLineDashPatternOperator(),
    b"ri": SetColourRenderingIntentOperator(),
    b"i": SetFlatnessToleranceOperator(),
    b"gs": SetParametersOperator(),

    b"m": BeginSubpathOperator(),
    b"l": AppendStraightLineOperator(),
    b"c": AppendCubicBezier1Operator(),
    b"v": AppendCubicBezier2Operator(),
    b"y": AppendCubicBezier3Operator(),
    b"h": ClosePathOperator(),
    b"re": AppendRectangleOperator(),

    # Table 60 – Path-Painting Operators
    b"S": StrokePathOperator(),
    b"s": CloseAndStrokePathOperator(),
    b"f": FillPathNZWOperator(),
    b"F": FillPathNZWOperator(),
    # Equivalent to f; included only for compatibility.
    b"f*": FillPathOEROperator(),
    b"B": FillAndStrokePathNZWOperator(),
    b"B*": FillAndStrokePathOEROperator(),
    b"b": CloseFillAndStrokePathNZWOperator(),
    b"b*": CloseFillAndStrokePathOEROperator(),
    b"n": EndPathOperator(),

    # Table 61 – Clipping Path Operators
    b"W": IntersectNZWOperator(),
    b"W*": IntersectOEROperator(),

    # Table 107 – Text object operators
    b"BT": BeginTextOperator(),
    b"ET": EndTextOperator(),

    # Table 108 – Text-positioning operators
    b"Td": MoveStartNextLineOperator(),
    b"TD": MoveStartNextLineTextStateOperator(),
    b"Tm": SetTextMatrixOperator(),
    b"T*": MoveStartNextLineWoParamsOperator(),

    # Table 109 – Text-showing operators
    b"Tj": ShowTextStringOperator(),
    b"'": MoveStartNextLineAndShowTextStringOperator(),
    b"\"": MoveStartNextLineAndShowTextStringWWordSpacingOperator(),
    b"TJ": ShowTextStringsOperator(),

    # Table 113 – Type 3 font operators
    b"d0": SetGlyphWidthOperator(),
    b"d1": SetGlyphBBOperator(),

    # Table 74 – Colour Operators
    b"CS": SetCurColourSpace1Operator(),
    b"cs": SetCurColourSpace1NonStrokingOperator(),
    b"SC": SetCurColourSpace2Operator(),
    b"SCN": SetCurColourSpace3Operator(),
    b"sc": SetCurColourSpace2NonStrokingOperator(),
    b"scn": SetCurColourSpace3NonStrokingOperator(),
    b"G": SetStrokingColourSpaceToGrayOperator(),
    b"g": SetStrokingColourSpaceToGrayNonStrokingOperator(),
    b"RG": SetStrokingColourSpaceToRGBOperator(),
    b"rg": SetStrokingColourSpaceToRGBNonStrokingOperator(),
    b"K": SetStrokingColourSpaceToCMYKOperator(),
    b"k": SetStrokingColourSpaceToCMYKNonStrokingOperator(),

    # Table 77 – Shading Operator
    b"sh": PaintShapeOperator(),

    # Table 92 – Inline Image Operators
    b"BI": BeginInlineImageOperator(),
    b"ID": BeginInlineImageDataOperator(),
    b"EI": EndInlineImageOperator(),

    # Table 87 – XObject Operator
    b"Do": PaintXObjectOperator(),

    # Table 320 – Marked-content operators
    b"MP": MarkedContentOperator(),
    b"DP": MarkedContentWListOperator(),
    b"BMC": BeginMarkedContentOperator(),
    b"BDC": BeginMarkedContentWPropertiesOperator(),
    b"EMC": EndMarkedContentOperator(),

    # Table 32 – Compatibility operators
    b"BX": BeginCompatibilityOperator(),
    b"EX": EndCompatibilityOperator(),

    ################################################
    # Table 105 – Text state operators
    b"Tc": SetCharSpacingOperator(),
    b"Tw": SetWordSpacingOperator(),
    b"Tz": SetHorizScalingOperator(),
    b"TL": SetTextLeadingOperator(),
    b"Tf": SetFontOperator(),
    b"Tr": SetTextRenderingModeOperator(),
    b"Ts": SetTextRiseOperator(),
}

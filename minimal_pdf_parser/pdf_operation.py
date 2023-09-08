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
from base import TextMatrix


class Operation:
    def __repr__(self) -> str:
        return "{}({})".format(self.__class__.__name__, ",".join(
            ["{}={}".format(x, y) for x, y in self.__dict__.items()]))


# Table 57 – Graphics State Operators

class SaveCurGraphicsState(Operation):
    pass


class RestoreCurGraphicsState(Operation):
    pass


class ModifyCTM(Operation):
    """
    8.3.4 Transformation Matrices
    x′ = a × x + c × y + e
    y′ = b × x + d × y + f
    """

    def __init__(self, a, b, c, d, e, f):
        self.a = a
        self.b = b
        self.c = c
        self.d = d
        self.e = e
        self.f = f


class SetLineWidth(Operation):
    def __init__(self, width):
        self.width = width


class SetLineCap(Operation):
    def __init__(self, cap):
        self.cap = cap


class SetLineJoin(Operation):
    def __init__(self, join):
        self.join = join


class SetMiterLimit(Operation):
    def __init__(self, miter_limit):
        self.miter_limit = miter_limit


class SetLineDashPattern(Operation):
    def __init__(self, dash_array, dash_phase):
        self.dash_array = dash_array
        self.dash_phase = dash_phase


class SetColourRenderingIntent(Operation):
    def __init__(self, intent):
        self.intent = intent


class SetFlatnessTolerance(Operation):
    def __init__(self, flatness):
        self.flatness = flatness


class SetParameters(Operation):
    def __init__(self, dict_name):
        self.dict_name = dict_name


# Table 59 – Path Construction Operators

class BeginSubpath(Operation):
    def __init__(self, x, y):
        self.x = x
        self.y = y


class AppendStraightLine(Operation):
    def __init__(self, x, y):
        self.x = x
        self.y = y


class AppendCubicBezier1(Operation):
    def __init__(self, x1, y1, x2, y2, x3, y3):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.x3 = x3
        self.y3 = y3


class AppendCubicBezier2(Operation):
    def __init__(self, x2, y2, x3, y3):
        self.x2 = x2
        self.y2 = y2
        self.x3 = x3
        self.y3 = y3


class AppendCubicBezier3(Operation):
    def __init__(self, x1, y1, x3, y3):
        self.x1 = x1
        self.y1 = y1
        self.x3 = x3
        self.y3 = y3


class ClosePath(Operation):
    pass


class AppendRectangle(Operation):
    def __init__(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h


# Table 60 – Path-Painting Operators

class StrokePath(Operation):
    pass


#
class SetFont(Operation):
    def __init__(self, name: bytes, size: float):
        self.name = name
        self.size = size



# Table 108 – Text-positioning operators

class SetTextMatrix(Operation):
    """
    See Table 108 – Text-positioning operators (continued)
    """

    def __init__(self, tm: TextMatrix):
        self.tm = tm

class UpdateTextMatrix(Operation):
    def __init__(self, w: float):
        self.w = w

class MoveStartNextLineWoParams(Operation):
    pass


class MoveStartNextLine(Operation):
    def __init__(self, tx: float, ty: float):
        self.tx = tx
        self.ty = ty



# Table 109 – Text-showing operators
class ShowTextString(Operation):
    def __init__(self, bs: bytes):
        self.bs = bs




# class MoveStartNextLineTextState(Operation):
#     def __init__(self, tx: float, ty: float):
#         self.tx = tx
#         self.ty = ty

# Table 105 – Text state operators
class SetCharSpacing(Operation):
    def __init__(self, char_space: float):
        self.char_space = char_space

class SetWordSpacing(Operation):
    def __init__(self, word_space: float):
        self.word_space = word_space

class SetTextLeading(Operation):
     def __init__(self, leading: float):
         self.leading = leading

class SetTextRise(Operation):
    def __init__(self, rise: float):
        self.rise = rise

class SetHorizScaling(Operation):
    def __init__(self, scale: float):
        self.scale = scale


# Table 107 – Text object operators
class BeginText(Operation):
    pass

class EndText(Operation):
    pass

__all__ = ['AppendCubicBezier1', 'AppendCubicBezier2', 'AppendCubicBezier3',
           'AppendRectangle', 'AppendStraightLine', 'BeginSubpath', 'BeginText', 'ClosePath', 'EndText',
           'ModifyCTM', 'MoveStartNextLine', 'SetTextLeading',
           'MoveStartNextLineWoParams', 'Operation',
           'RestoreCurGraphicsState',
           'SaveCurGraphicsState', 'SetColourRenderingIntent',
           'SetFlatnessTolerance', 'SetFont', 'SetLineCap',
           'SetLineDashPattern', 'SetLineJoin', 'SetLineWidth', 'SetMiterLimit',
           'SetParameters', 'ShowTextString', 'SetTextMatrix', 'UpdateTextMatrix']  # 'TD', 'Td',

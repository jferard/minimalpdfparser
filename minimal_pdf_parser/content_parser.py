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
from typing import Iterator, Mapping

from base import (WordToken, ArrayObject, checked_cast, NumberObject,
                  StringObject)
from pdf_operator import (Operation, TokenQueue, operator_by_token_bytes,
                          )
from tokenizer import (PDFTokenizer, StreamWrapper)


class ContentParser:
    _logger = logging.getLogger(__name__)

    def parse_content(self, stream_wrapper: StreamWrapper
                      ) -> Iterator[Operation]:
        stack = TokenQueue()

        # See : Table A.1 – PDF content stream operators
        for token in PDFTokenizer(stream_wrapper):
            if isinstance(token, WordToken):
                token_bytes = token.bs
                try:
                    operator = operator_by_token_bytes[token_bytes]
                    for operation in operator.build(stack):
                        yield operation
                except KeyError:
                    self._logger.warning("Unk token name %s", token_bytes)
            else:
                stack.push(token)

    def parse_to_unicode(self, stream_wrapper: StreamWrapper
                         ) -> Mapping[int, str]:
        """
        9.7.5.4 CMap Example and Operator Summary

        :param stream_wrapper:
        :return:
        """
        stack = []

        fchar_count = 0
        frange_count = 0
        encoding = {}
        for token in PDFTokenizer(stream_wrapper):
            if isinstance(token, WordToken):
                token_bytes = token.bs
                if token_bytes == b"beginbfchar":
                    fchar_count = checked_cast(NumberObject, stack[0]).value
                elif token_bytes == b"endbfchar":
                    for i in range(0, fchar_count, 2):
                        first = checked_cast(StringObject, stack[i]).bs
                        second = checked_cast(StringObject, stack[i + 1]).bs
                        code = int.from_bytes(first, "big")
                        encoding[code] = second.decode("utf-16-be")
                elif token_bytes == b"beginbfrange":
                    frange_count = checked_cast(NumberObject, stack[0]).value
                elif token_bytes == b"endbfrange":
                    for i in range(0, frange_count, 3):
                        first = checked_cast(StringObject, stack[i]).bs
                        second = checked_cast(StringObject, stack[i + 1]).bs
                        third = stack[i + 2]
                        first_code = int.from_bytes(first, "big")
                        second_code = int.from_bytes(second, "big")
                        if isinstance(third, ArrayObject):
                            for code, value in enumerate(third, first_code):
                                bs = checked_cast(StringObject, value).bs
                                encoding[code] = bs.decode("utf-16-be")
                        elif isinstance(third, StringObject):
                            cur_value = third.bs.decode("utf-16-be")
                            for code in range(first_code, second_code):
                                encoding[code] = cur_value
                                cur_value = chr(ord(cur_value) + 1)
                        else:
                            raise ValueError()

                stack = []
            else:
                stack.append(token)
        return encoding



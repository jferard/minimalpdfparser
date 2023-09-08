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
import sys
from pathlib import Path
from typing import TextIO, BinaryIO

from parser import PDFParser
from tool import TextProcessor, extract_text, RawTextProcessor

SPACE = 0x20

STARTXREF = b'startxref'
LEN_STARTXREF = len(STARTXREF)


def main(path: Path):
    if args.processor == "R":
        processor = RawTextProcessor()
    else:
        processor = TextProcessor()
    if args.input is None:
        if args.output is None:
            extract(processor, sys.stdin.buffer, sys.stdout)
        else:
            with Path(args.output).open("w", encoding="utf-8") as d:
                extract(processor, sys.stdin.buffer, d)
    else:
        with Path(args.input).open("rb") as s:
            if args.output is None:
                extract(processor, s, sys.stdout)
            else:
                with Path(args.output).open("w", encoding="utf-8") as d:
                    extract(processor, s, d)


def extract(processor: TextProcessor, s: BinaryIO, d: TextIO):
    parser = PDFParser(s)
    document = parser.parse()
    extract_text(document, processor, d)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--processor", type=str, choices=["N", "R"],
                        required=False,
                        help="processor file, N for normal, R for raw")
    parser.add_argument("-i", "--input", type=str, help="input file, stdin if absent")
    parser.add_argument("-o", "--output", type=str, help="output file, stdout if absent")
    parser.parse_args()
    args = parser.parse_args()
    main(args)

    print(args.processor, args.input, args.output)
    # TODO : option for text processor
    # main(Path(sys.argv[1]))

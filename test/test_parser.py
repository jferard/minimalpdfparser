import io
import logging
import unittest
from pathlib import Path
from unittest import mock

from base import (NameObject, ArrayObject, DictObject,
                  IndirectRef, NumberObject)
from font_parser import FontParser
from parser import PDFParser, ObjectParser
from pdf_encodings import ENCODING_BY_NAME, UNICODE_BY_GLYPH_NAME
from tokenizer import PDFTokenizer, BinaryStreamWrapper
from tool import TextProcessor, extract_text

FIXTURE_PATH = Path(__file__).parent.parent / "fixture"


class TestCase(unittest.TestCase):
    def test_parser(self):
        with (FIXTURE_PATH / "rfc788.txt.pdf").open("rb") as s:
            parser = PDFParser(s)
            document = parser.parse()
            for t in document.extract_text():
                print(t.s)

    def test_parser2(self):
        logging.basicConfig(level=logging.DEBUG, filename="test2.log",
                            filemode="w",
                            format='[%(asctime)s] {%(filename)s:%(funcName)s:%(lineno)d} %(levelname)s - %(message)s')
        path = (FIXTURE_PATH / "PDF32000_2008.pdf")
        with path.open("rb") as s:
            parser = PDFParser(s)
            document = parser.parse()
            with (FIXTURE_PATH / "PDF32000_2008.txt").open("w") as d:
                extract_text(document, TextProcessor(), d)

    def test_object_parser(self):
        s = io.BytesIO(b"""<<
/Type /Page
/MediaBox [0 0 612 792]
/Parent 2 0 R
/Resources << /ProcSet [/PDF /Text]
/Font <<
/R6 6 0 R
>>
>>
/Contents 8 0 R
>>""")
        tokenizer = PDFTokenizer.create(s)
        self.assertEqual(
            DictObject({
                b'/Type': NameObject(bs=b'/Page'),
                b'/MediaBox': ArrayObject(arr=[
                    NumberObject(bs=b'0'), NumberObject(bs=b'0'),
                    NumberObject(bs=b'612'), NumberObject(bs=b'792')
                ]),
                b'/Parent': IndirectRef(
                    obj_num=NumberObject(bs=b'2'),
                    gen_num=NumberObject(bs=b'0')
                ),
                b'/Resources': DictObject({
                    b'/ProcSet': ArrayObject([
                        NameObject(bs=b'/PDF'), NameObject(bs=b'/Text')
                    ]),
                    b'/Font': DictObject({
                        b'/R6': IndirectRef(
                            obj_num=NumberObject(bs=b'6'),
                            gen_num=NumberObject(bs=b'0')
                        )
                    })
                }),
                b'/Contents': IndirectRef(
                    obj_num=NumberObject(bs=b'8'),
                    gen_num=NumberObject(bs=b'0')
                )
            })
            , ObjectParser(tokenizer).parse())

    def test_stream_wrapper(self):
        bsw = BinaryStreamWrapper(io.BytesIO(b"foo bar baz"))
        bsw.unget()
        self.assertEqual(102, next(bsw))
        self.assertEqual(111, next(bsw))
        self.assertEqual(111, next(bsw))
        self.assertEqual(32, next(bsw))
        bsw.unget()
        self.assertEqual(32, next(bsw))
        self.assertEqual(98, next(bsw))
        self.assertEqual(97, next(bsw))
        self.assertEqual(114, next(bsw))
        self.assertEqual(32, next(bsw))
        self.assertEqual(98, next(bsw))
        self.assertEqual(97, next(bsw))
        self.assertEqual(122, next(bsw))
        with self.assertRaises(StopIteration):
            next(bsw)
        bsw.unget()
        self.assertEqual(122, next(bsw))


class FontParserTestCase(unittest.TestCase):
    def test_font_parser(self):
        s = io.BytesIO(b"""<< /Type /Font
/Subtype /Type1
/Encoding 21 0 R
/BaseFont /ZapfDingbats
>>""")
        tokenizer = PDFTokenizer.create(s)
        font_object = ObjectParser(tokenizer).parse()
        print(font_object)

    def test_encoding_parser(self):
        s = io.BytesIO(b"""<< /Type /Encoding
/Differences
[
39 /quotesingle
96 /grave
128 /Adieresis /Aring /Ccedilla /Eacute /Ntilde /Odieresis /Udieresis
/aacute /agrave /acircumflex /adieresis /atilde /aring /ccedilla
/eacute /egrave /ecircumflex /edieresis /iacute /igrave /icircumflex
/idieresis /ntilde /oacute /ograve /ocircumflex /odieresis /otilde
/uacute /ugrave /ucircumflex /udieresis /dagger /degree /cent
/sterling /section /bullet /paragraph /germandbls /registered
/copyright /trademark /acute /dieresis
174 /AE /Oslash
177 /plusminus
180 /yen /mu
187 /ordfeminine /ordmasculine
190 /ae /oslash /questiondown /exclamdown /logicalnot
196 /florin
199 /guillemotleft /guillemotright /ellipsis
203 /Agrave /Atilde /Otilde /OE /oe /endash /emdash /quotedblleft
/quotedblright /quoteleft /quoteright /divide
216 /ydieresis /Ydieresis /fraction /currency /guilsinglleft /guilsinglright
/fi /fl /daggerdbl /periodcentered /quotesinglbase /quotedblbase
/perthousand /Acircumflex /Ecircumflex /Aacute /Edieresis /Egrave
/Iacute /Icircumflex /Idieresis /Igrave /Oacute /Ocircumflex
241 /Ograve /Uacute /Ucircumflex /Ugrave /dotlessi /circumflex /tilde
/macron /breve /dotaccent /ring /cedilla /hungarumlaut /ogonek
/caron
]
>>""")
        document = mock.Mock()
        document.get_object = lambda x: x

        tokenizer = PDFTokenizer.create(s)
        encoding_object = ObjectParser(tokenizer).parse()
        be = {}
        encoding = FontParser(document, UNICODE_BY_GLYPH_NAME,
                              ENCODING_BY_NAME)._apply_differences(
            encoding_object, be)
        print(encoding)


if __name__ == "__main__":
    unittest.main()

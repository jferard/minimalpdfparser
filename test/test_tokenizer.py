import io
import unittest
from pathlib import Path

from minimal_pdf_parser.tokenizer import PDFTokenizer
from minimal_pdf_parser.base import OpenArrayToken, CloseArrayToken, StringObject, NameObject


FIXTURE_PATH = Path(__file__).parent.parent / "fixture"


class TokenizerTestCase(unittest.TestCase):
    def test_id(self):
        s = b"/ID [<9597C618BC90AFA4A078CA72B2DD061C> <48726007F483D547A8BEFF6E9CDA072F>]"
        tokenizer = PDFTokenizer.create(io.BytesIO(s))
        self.assertEqual([
            NameObject(bs=b'/ID'),
            OpenArrayToken,
            StringObject(bs=b'\x95\x97\xc6\x18\xbc\x90\xaf\xa4\xa0x\xcar\xb2\xdd\x06\x1c'),
            StringObject(bs=b'Hr`\x07\xf4\x83\xd5G\xa8\xbe\xffn\x9c\xda\x07/'),
            CloseArrayToken
        ], list(tokenizer))

    def test_u_o(self):
        s = b"""/O <63981688733872DEC7983D3C6EB1F412CC535EA2DAA2AB171E2BBC4E36B21887>
/U <D64AB15C7434FFE1732E6388274F64C428BF4E5E4E758A4164004E56FFFA0108>"""
        tokenizer = PDFTokenizer.create(io.BytesIO(s))
        self.assertEqual([
            NameObject(bs=b'/O'),
            StringObject(bs=b'c\x98\x16\x88s8r\xde\xc7\x98=<n\xb1\xf4\x12\xccS^\xa2\xda\xa2\xab\x17\x1e+\xbcN6\xb2\x18\x87'),
            NameObject(bs=b'/U'),
            StringObject(bs=b"\xd6J\xb1\\t4\xff\xe1s.c\x88'Od\xc4(\xbfN^Nu\x8aAd\x00NV\xff\xfa\x01\x08"),
        ], list(tokenizer))

    def test_string_example_1_1(self):
        s = b"(This is a string.)"
        tokenizer = PDFTokenizer.create(io.BytesIO(s))
        self.assertEqual([StringObject(bs=b'This is a string.')], list(tokenizer))

    def test_string_example_1_2(self):
        s = b"""(Strings may contain newlines
and such.)"""
        tokenizer = PDFTokenizer.create(io.BytesIO(s))
        self.assertEqual([StringObject(bs=b'Strings may contain newlines\nand such.')],
                 list(tokenizer))

    def test_string_example_1_3(self):
        s = b"""(Strings may contain balanced parentheses () and
special characters (*!&}^% and so on).)"""
        tokenizer = PDFTokenizer.create(io.BytesIO(s))
        self.assertEqual([StringObject(bs=b'Strings may contain balanced parentheses () and\nspecial characters (*!&}^% and so on).')],
                 list(tokenizer))

    def test_string_example_1_4(self):
        s = b"(The following is an empty string .)"
        tokenizer = PDFTokenizer.create(io.BytesIO(s))
        self.assertEqual([StringObject(bs=b'The following is an empty string .')],
                 list(tokenizer))

    def test_string_example_1_5(self):
        s = b"()"
        tokenizer = PDFTokenizer.create(io.BytesIO(s))
        self.assertEqual([StringObject(bs=b'')], list(tokenizer))

    def test_string_example_1_6(self):
        s = b"(It has zero (0) length.)"
        tokenizer = PDFTokenizer.create(io.BytesIO(s))
        self.assertEqual([StringObject(bs=b'It has zero (0) length.')],
                 list(tokenizer))

    def test_string_example_2(self):
        s = b"""(These \\
two strings \\
are the same.)"""
        tokenizer = PDFTokenizer.create(io.BytesIO(s))
        self.assertEqual([StringObject(bs=b'These two strings are the same.')], list(tokenizer))

    def test_string_example_3_1(self):
        s = b"""(This string has an end-of-line at the end of it.
)"""
        tokenizer = PDFTokenizer.create(io.BytesIO(s))
        self.assertEqual([StringObject(bs=b'This string has an end-of-line at the end of it.\n')], list(tokenizer))

    def test_string_example_3_2(self):
        s = b"(So does this one.\n)"
        tokenizer = PDFTokenizer.create(io.BytesIO(s))
        self.assertEqual([StringObject(bs=b'So does this one.\n')], list(tokenizer))

    def test_string_example_4(self):
        s = b"(This string contains \\245two octal characters\\307.)"
        tokenizer = PDFTokenizer.create(io.BytesIO(s))
        self.assertEqual([StringObject(bs=b'This string contains \xa5two octal characters\xc7.')], list(tokenizer))

    def test_string_example_5_1(self):
        s = b"(\\0053)"
        tokenizer = PDFTokenizer.create(io.BytesIO(s))
        self.assertEqual([StringObject(bs=b'\x053')], list(tokenizer))

    def test_string_example_5_2(self):
        s = b"(\\053)"
        tokenizer = PDFTokenizer.create(io.BytesIO(s))
        self.assertEqual([StringObject(bs=b'\x2b')], list(tokenizer))

    def test_string_example_5_3(self):
        s = b"(\\53)"
        tokenizer = PDFTokenizer.create(io.BytesIO(s))
        self.assertEqual([StringObject(bs=b'\x2b')], list(tokenizer))

    def test_tokenizer(self):
        with (FIXTURE_PATH / "rfc776.txt.pdf").open("rb") as s:
            pdf_tokenizer = PDFTokenizer.create(s)
            for x in pdf_tokenizer:
                print(x)

    def test_tokens(self):
        contents = b"Td(   \\(but not the whole mail transaction\\).  The SMTP-sender and)"
        pdf_tokenizer = PDFTokenizer.create(io.BytesIO(contents))
        for x in pdf_tokenizer:
            print(x)



if __name__ == '__main__':
    unittest.main()

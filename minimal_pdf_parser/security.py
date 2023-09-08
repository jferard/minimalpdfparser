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
from hashlib import md5
from typing import List, BinaryIO

from tokenizer import _bytes_to_string

PADDING_STRING = (b"\x28\xbf\x4e\x5e\x4e\x75\x8a\x41"
                  b"\x64\x00\x4e\x56\xff\xfa\x01\x08"
                  b"\x2e\x2e\x00\xb6\xd0\x68\x3e\x80"
                  b"\x2f\x0c\xa9\xfe\x64\x53\x69\x7a")


class Encrypter:
    """An encrypter/decrypter"""
    def __init__(self, encryption_key: bytes, version: int, aes: bool = False):
        self.encryption_key = encryption_key
        self.version = version
        self.aes = aes

    def encrypt_data(self, obj_num: int, gen_num: int, data: bytes):
        """
        Algorithm 1: Encryption of data using the RC4 or AES algorithms
        """
        key = self.get_rc4_key(obj_num, gen_num)

        # If using the AES algorithm, the Cipher Block Chaining (CBC) mode, which requires an initialization vector,
        # is used. The block size parameter is set to 16 bytes, and the initialization vector is a 16-byte random
        # number that is stored as the first 16 bytes of the encrypted stream or string.
        if self.aes:
            pass  # take the 16 fiurst bytes as IV

        return ARC4(key, data)

    def chunks_encrypter(self, obj_num: int, gen_num: int):
        """
        Algorithm 1: Encryption of data using the RC4 or AES algorithms
        """
        key = self.get_rc4_key(obj_num, gen_num)

        # If using the AES algorithm, the Cipher Block Chaining (CBC) mode, which requires an initialization vector,
        # is used. The block size parameter is set to 16 bytes, and the initialization vector is a 16-byte random
        # number that is stored as the first 16 bytes of the encrypted stream or string.
        if self.aes:
            pass  # take the 16 fiurst bytes as IV

        return ARC4_iterator(key)

    def encrypt_stream(self, obj_num: int, gen_num: int, s: BinaryIO,
                       d: BinaryIO):
        """
        Algorithm 1: Encryption of data using the RC4 or AES algorithms
        """
        key = self.get_rc4_key(obj_num, gen_num)

        # If using the AES algorithm, the Cipher Block Chaining (CBC) mode, which requires an initialization vector,
        # is used. The block size parameter is set to 16 bytes, and the initialization vector is a 16-byte random
        # number that is stored as the first 16 bytes of the encrypted stream or string.
        if self.aes:
            pass  # take the 16 fiurst bytes as IV

        return ARC4_stream(key, s, d)

    def get_rc4_key(self, obj_num: int, gen_num: int) -> bytes:
        # a)Obtain the obj number and generation number from the obj identifier of the string or stream to be
        # encrypted (see 7.3.10, "Indirect Objects"). If the string is a direct obj, use the identifier of the indirect
        # obj containing it.
        # b)For all strings and streams without crypt filter specifier; treating the obj number and generation number
        # as binary integers, extend the original n-byte encryption key to n + 5 bytes by appending the low-order 3
        # bytes of the obj number and the low-order 2 bytes of the generation number in that order, low-order byte
        # first. (n is 5 unless the value of V in the encryption dictionary is greater than 1, in which case n is the value
        # of Length divided by 8.)
        obj_num_bytes = struct.pack("<i", obj_num)[:3]
        gen_num_bytes = struct.pack("<i", gen_num)[:2]
        key = self.encryption_key + obj_num_bytes + gen_num_bytes
        # If using the AES algorithm, extend the encryption key an additional 4 bytes by adding the value “sAlT”,
        # which corresponds to the hexadecimal values 0x73, 0x41, 0x6C, 0x54. (This addition is done for backward
        # compatibility and is not intended to provide additional security.)
        if self.aes:
            key += b"\x73\x41\x6C\x54"
        # c)Initialize the MD5 hash function and pass the result of step (b) as input to this function.
        hasher = md5(key)
        # d)Use the first (n + 5) bytes, up to a maximum of 16, of the output from the MD5 hash as the key for the RC4
        # or AES symmetric key algorithms, along with the string or stream data to be encrypted.
        digest = hasher.digest()
        k = len(key)
        if k > 16:
            k = 16
        return digest[:k]


class StandardEncrypterFactory:
    """
    A translation from /Filter obj
    """
    def __init__(self, doc_id: List[bytes], version: int, revision_num: int,
                 length, permissions: int, hashed_owner_and_user_passwd: bytes,
                 hashed_user_passwd: bytes):
        self.doc_id = doc_id
        self.version = version
        self.revision_num = revision_num
        self.length = length
        self.permissions = permissions
        self.hashed_owner_and_user_passwd = hashed_owner_and_user_passwd
        self.hashed_user_passwd = hashed_user_passwd

    def create(self, password=b"") -> Encrypter:
        """
        Algorithm 2: Computing an encryption key
        """
        # a) Pad or truncate the password string to exactly 32 bytes. If the password string is more than 32 bytes long,
        # use only its first 32 bytes; if it is less than 32 bytes long, pad it by appending the required number of
        # additional bytes from the beginning of the following padding string:
        # < 28 BF 4E 5E 4E 75 8A 41 64 00 4E 56 FF FA 01 08
        # 2E 2E 00 B6 D0 68 3E 80 2F 0C A9 FE 64 53 69 7A >
        # That is, if the password string is n bytes long, append the first 32 - n bytes of the padding string to the end
        # of the password string. If the password string is empty (zero-length), meaning there is no user password,
        # substitute the entire padding string in its place.
        bs = (password + PADDING_STRING)[:32]
        # b)Initialize the MD5 hash function and pass the result of step (a) as input to this function.
        hasher = md5(bs)
        # c)Pass the value of the encryption dictionary’s O entry to the MD5 hash function. ("Algorithm 3: Computing
        # the encryption dictionary’s O (owner password) value" shows how the O value is computed.)
        hasher.update(self.hashed_owner_and_user_passwd)
        # d)Convert the integer value of the P entry to a 32-bit unsigned binary number and pass these bytes to the
        # MD5 hash function, low-order byte first.
        f = struct.pack("<i", self.permissions)
        hasher.update(f)
        # e)Pass the first element of the file’s file identifier array (the value of the ID entry in the self’s trailer
        # dictionary; see Table 15) to the MD5 hash function.
        hasher.update(self.doc_id[0])
        # f)(Security handlers of revision 4 or greater) If self metadata is not being encrypted, pass 4 bytes with
        # the value 0xFFFFFFFF to the MD5 hash function.
        if self.revision_num >= 4:
            hasher.update(b"0xff0xff0xff0xff")
        # g)Finish the hash.
        digest = hasher.digest()
        # h)(Security handlers of revision 3 or greater) Do the following 50 times: Take the output from the previous
        # MD5 hash and pass the first n bytes of the output as input into a new MD5 hash, where n is the number of
        # bytes of the encryption key as defined by the value of the encryption dictionary’s Length entry.
        if self.revision_num >= 3:
            length = self.length // 8
            for _ in range(50):
                digest = md5(digest[:length]).digest()

        # i)Set the encryption key to the first n bytes of the output from the final MD5 hash, where n shall always be 5
        # for security handlers of revision 2 but, for security handlers of revision 3 or greater, shall depend on the
        # value of the encryption dictionary’s Length entry.
        if self.revision_num == 2:
            length = 5
        else:
            length = self.length // 8
        encryption_key = digest[:length]
        return Encrypter(encryption_key, self.version)


def ARC4_stream(key: bytes, s: BinaryIO, d: BinaryIO):
    """
    See https://en.wikipedia.org/w/index.php?title=RC4&oldid=1092702151#Description

    :param key:
    :param s:
    :param d:
    :return:
    """
    permutation = _init_ARC4(key)

    i = 0
    j = 0
    bytes_read = s.read(1)
    while bytes_read != b'':
        b = bytes_read[0]
        i = (i + 1) & 0xFF
        j = (j + permutation[i]) & 0xFF
        permutation[i], permutation[j] = permutation[j], permutation[i]
        cipher_byte = permutation[(permutation[i] + permutation[j]) & 0xFF]
        d.write(struct.pack("B", b ^ cipher_byte))
        bytes_read = s.read(1)


def ARC4(key: bytes, data: bytes) -> bytes:
    """
    See https://en.wikipedia.org/w/index.php?title=RC4&oldid=1092702151#Description
    :param key:
    :param data:
    :return:
    """
    permutation = _init_ARC4(key)

    ret = []
    i = 0
    j = 0
    for b in data:
        i = (i + 1) & 0xFF
        j = (j + permutation[i]) & 0xFF
        permutation[i], permutation[j] = permutation[j], permutation[i]
        cipher_byte = permutation[(permutation[i] + permutation[j]) & 0xFF]
        ret.append(b ^ cipher_byte)

    return _bytes_to_string(ret)


class ARC4_iterator:
    """
    See https://en.wikipedia.org/w/index.php?title=RC4&oldid=1092702151#Description
    :param key:
    :param data:
    :return:
    """

    def __init__(self, key: bytes):
        self.permutation = _init_ARC4(key)
        self.i = 0
        self.j = 0

    def chunk(self, data: bytes) -> bytes:
        ret = []
        for b in data:
            self.i = (self.i + 1) & 0xFF
            self.j = (self.j + self.permutation[self.i]) & 0xFF
            self.permutation[self.i], self.permutation[self.j] = self.permutation[
                                                                      self.j], self.permutation[
                self.i]
            cipher_byte = self.permutation[
                (self.permutation[self.i] + self.permutation[self.j]) & 0xFF]
            ret.append(b ^ cipher_byte)

        return _bytes_to_string(ret)


def _init_ARC4(key: bytes):
    permutation = list(range(256))
    len_key = len(key)
    j = 0
    for i in range(256):
        j = (j + permutation[i] + key[i % len_key]) & 0xFF
        permutation[i], permutation[j] = permutation[j], permutation[i]
    return permutation

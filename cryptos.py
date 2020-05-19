# This file is part of twnhi-smartcard-agent.
#
# twnhi-smartcard-agent is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# twnhi-smartcard-agent is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with twnhi-smartcard-agent.
# If not, see <https://www.gnu.org/licenses/>.

import os
import datetime
import hashlib
from Cryptodome.Cipher import DES, DES3

bKEY = b'12345678123456780' * 10
K_BOX = [
    0x56, 0x28, 0x34, 0x2E, 0x78, 0x5,  0xF,  0x5A,
    0x36, 0x44, 0x42, 0x19, 0x26, 0x95, 0x26, 0x4D,
    0x3,  0x10, 0x15, 0x58, 0x3,  0x40, 0x5A, 0x72,
    0x1E, 0xB,  0x49, 0x69, 0x4B, 0x15, 0x29, 0x6
]
K_BOX1 = [
    0x56, 0x28, 0x34, 0x2E, 0x78, 0x5,  0xF,  0x5A,
    0x36, 0x44, 0x42, 0x19, 0x26, 0x95, 0x26, 0x4D,
    0x2D, 0x41, 0x4D, 0x1F, 0x41, 0x62, 0x15, 0x2F
]

L_KEY = bytes(bKEY[K_BOX[i]] for i in range(16)) + b'\0' * 8
L_KEY1 = bytes(bKEY[K_BOX1[i]] for i in range(24))

KEY_SUFFIX = b'\x27\x06\x58\x66'

TDesLKey = DES3.new(L_KEY, DES3.MODE_ECB)
TDesLKey1 = DES3.new(L_KEY1, DES3.MODE_ECB)

def iv_pad(d):
    def rand_byte():
        return os.urandom(1)
    bcount = len(d) // 7
    if len(d) % 7:
        bcount += 1

    blocks = [ d[i*7:i*7 + 7].ljust(7, b'\0') + rand_byte() for i in range(bcount) ]
    return b''.join(blocks)

def iv_remove(d, flag=True):
    c = b''.join(d[i*8:i*8+7] for i in range(len(d) // 8))
    if flag:
        unpad_size = (len(c) // 8) * 8
        return c[:unpad_size]
    return c

def pkcs5_tail(n):
    return bytes([n]) * n

def pkcs5_pad(data):
    padding_size = 8 - len(data) % 8
    return data + pkcs5_tail(padding_size)

def pkcs5_unpad(data):
    last_byte = data[-1]
    tail = data[-last_byte:]
    if last_byte > 8 or bytes(tail) != pkcs5_tail(last_byte):
        raise ValueError('Inalid PKCS5 padding')
    return data[:-last_byte]

def card_encrypt(data, cardid):
    t = datetime.date.today().strftime('%Y%m%d')
    tdeskey = hashlib.sha1((cardid + t).encode('ascii')).digest() + KEY_SUFFIX
    cipher = DES3.new(tdeskey, DES3.MODE_ECB)

    data = cipher.encrypt(pkcs5_pad(data))
    return TDesLKey1.encrypt(iv_pad(data))

def card_decrypt(data, cardid):
    t = datetime.date.today().strftime('%Y%m%d')
    tdeskey = hashlib.sha1((cardid + t).encode('ascii')).digest() + KEY_SUFFIX
    cipher = DES3.new(tdeskey, DES3.MODE_ECB)

    data = TDesLKey1.decrypt(data)
    data = iv_remove(data)
    data = cipher.decrypt(data)
    return pkcs5_unpad(data)

def basic_encrypt(data):
    key = datetime.date.today().strftime('%m%d%Y').encode('ascii')
    cipher = DES.new(key, DES.MODE_ECB)
    return cipher.encrypt(iv_pad(data))

def basic_decrypt(data):
    key = datetime.date.today().strftime('%m%d%Y').encode('ascii')
    cipher = DES.new(key, DES.MODE_ECB)
    decrypted = cipher.decrypt(data)
    return iv_remove(decrypted, False)

if __name__ == '__main__':
    data, card_id = b'123456123456', '000000000001'
    if card_decrypt(card_encrypt(data, card_id), card_id) == data:
        print('card_* : Pass')
    else:
        print('card_* : Failed')

    for i in range(40, 40+2*6):
        test_data = bytes(range(i))
        if basic_decrypt(basic_encrypt(test_data + b'\xff')).split(b'\xff')[0] != test_data:
            print('basic_* : Failed')
            break
    else:
        print('basic_* : Pass')

    import sys
    if len(sys.argv) > 1:
        data = bytes.fromhex(sys.argv[1])
        print(basic_decrypt(data).decode('big5-hkscs'))

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
import socket

from hexdump import hexdump

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from cryptos import DES3, pkcs5_pad, pkcs5_unpad, L_KEY
from errors import ServiceError

DEBUG = bool(os.getenv('DEBUG_MODE', None))

DEFAULT_HOST = os.getenv('NIC_SMARTCARD_AUTH_HOST', 'cloudicap.nhi.gov.tw')
DEFAULT_PORT = int(os.getenv('NIC_SMARTCARD_AUTH_HOST', 443))

def recvall(conn, err_code, err_desc):
    data = b''
    while not data.endswith(b'<E>'):
        try:
            data += conn.recv(4096)
        except Exception as e:
            raise ServiceError(err_code, err_desc, e)

    return data

def send_packet(conn, data, error_code, description):
    try:
        conn.sendall(data)
    except Exception as e:
        raise ServiceError(error_code, description, e)

def encrypt(key, data):
    cipher = DES3.new(key, DES3.MODE_ECB)
    encrypted = cipher.encrypt(pkcs5_pad(data))
    return encrypted + b'<E>'

def decrypt(key, data):
    # funciton `recvall` already ensures that data will end with b'<E>'
    assert data.endswith(b'<E>')

    cipher = DES3.new(key, DES3.MODE_ECB)
    decrypted = cipher.decrypt(data[:-3])
    return pkcs5_unpad(decrypted)

def debug_dump(name, data):
    if DEBUG:
        print('%s:' % name)
        hexdump(data)

def handshake(conn):
    try:
        # generate rsa key for handshake
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=1024,
            backend=default_backend()
        )
    except Exception as e:
        raise ServiceError(8300, 'Failed to generate RSA key', e)

    # hello packet, send our public key
    try:
        pubkey = private_key.public_key().public_bytes(
           encoding=serialization.Encoding.PEM,
           format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).rstrip(b'\n')
    except Exception as e:
        raise ServiceError(8301, 'Failed to dump public key', e)

    data = b'Hello %s' % pubkey
    debug_dump('Local hello', data)
    send_packet(conn, encrypt(L_KEY, data), 8306, 'Failed to send handshake packet')

    # recv remote hello
    packet = recvall(conn, 8305, 'Recv error')
    try:
        data = decrypt(L_KEY, packet)
        debug_dump('Remote hello', data)
        assert data[:5] == b'Hello'
    except Exception as e:
        raise ServiceError(8305, 'Decrypt error', e)

    # decrypt remote nonce
    try:
        remote_nonce = private_key.decrypt(data[0x11b:0x11b+0x80], padding.PKCS1v15())
    except Exception as e:
        raise ServiceError(8305, 'RSA decrypt error', e)

    # prepare and encrypt our nonce with remote public key
    nonce = os.urandom(16)
    try:
        remote_public = serialization.load_pem_public_key(
            data[6:0x116],
            backend=default_backend()
        )
        enc_nonce = remote_public.encrypt(nonce, padding.PKCS1v15())
    except Exception as e:
        raise ServiceError(8303, 'Pubkey encrypt failed', e)

    send_packet(conn, b' %d %s<E>' % (len(enc_nonce), enc_nonce), 8304, \
            'Failed to send nonce')

    # concat nonces to make session key
    return (nonce + remote_nonce)[:24]

def connect(host=DEFAULT_HOST, port=DEFAULT_PORT):
    try:
        return socket.create_connection((host, port))
    except Exception as e:
        raise ServiceError(4061, 'Can not connect to host', e)

def sam_hc_auth_check(raise_on_failed=False):
    with connect() as conn:
        sess_key = handshake(conn)
        send_packet(conn, b'77<E>', 8003, 'Failed to send test packet')
        ret = recvall(conn, 8005, 'Service check failed') == b'04<rc=2>OK<E>'

        if not ret and raise_on_failed:
            raise ServiceError(8005, 'Service check failed')
        return ret

def sam_hc_auth(client, to_sign):
    with connect() as conn:
        sess_key = handshake(conn)

        # prepare data to be signed
        client.select_applet()
        hcid = client.get_hc_card_id()
        rnd = client.get_random()

        # send auth request
        assert len(hcid) == 12 and len(rnd) == 8
        data = b'01<id=12>%s<rn=8>%s<E>' % (hcid, rnd)
        packet = encrypt(sess_key, data)
        send_packet(conn, packet, 8003, 'Failed to send auth request 01')

        # recv challenge
        packet = recvall(conn, 8005, 'Failed to recv challenge')
        data = decrypt(sess_key, packet)
        debug_dump('Challenge', data)
        # b'02<au=32>................................<E>'
        if not (data.startswith(b'02<au=32>') and data.endswith(b'<E>')):
            raise ServiceError(8005, 'Failed to decrypt challenge')
        challenge = data[9:9+32]

        # use hccard to sign challenge
        response = client.muauth_hc_dc_sam(challenge)
        debug_dump('Response', response)
        if len(response) != 16:
            raise ServiceError(8006, 'Invalid data length from SAM signing')

        # send challenge and data to be signed
        if len(to_sign) != 20:
            raise ServiceError(8006, 'Invalid data length `to_sign`')

        data = b'03<au=16>%s<se=20>%s<E>' % (response, to_sign)
        packet = encrypt(sess_key, data)
        send_packet(conn, packet, 8007, 'Failed to send response')

        # got signature
        data = decrypt(sess_key, recvall(conn, 8008, 'Failed to recv signature'))
        debug_dump('Signature', data)
        # b'04<rc=2>OK<si=256>' ...(256bytes) b'<E>'
        if not (data.startswith(b'04<rc=2>OK<si=256>') and data.endswith(b'<E>')):
            raise ServiceError(8008, 'Failed to decrypt signature')
        return data[18:-3]

if __name__ == '__main__':
    sam_hc_auth_check()
    from hccard import HealthInsuranceSmartcardClient
    with HealthInsuranceSmartcardClient() as client:
        sig = sam_hc_auth(client, b'00011234123412341234')
        print('sig = %r' % sig)

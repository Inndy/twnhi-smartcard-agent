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

#!/usr/bin/env python3
import asyncio
import atexit
import contextlib
import http
import logging
import os
import ssl
import subprocess
import sys
import threading

import websockets
from hccard import HealthInsuranceSmartcardClient, select_reader_and_connect, \
        SmartcardCommandException
from cryptos import card_encrypt, basic_encrypt
from complicated_sam_hc_auth import sam_hc_auth, sam_hc_auth_check
from errors import ServiceError

logging.basicConfig(level='INFO', stream=sys.stdout)
logger = logging.getLogger('server')

HOST = 'iccert.nhi.gov.tw'
CENSORED_COMMANDS = ['EnCrypt', 'SecureGetBasicWithParam', 'GetBasic']

lock = threading.Lock()

class HTTP(websockets.WebSocketServerProtocol):
    async def process_request(self, path, request_headers):
        if path == '/echo':
            return await super().process_request(path, request_headers)
        elif path == '/exit':
            exit()
        elif path == '/':
            body = b'It works!\n'
            return http.HTTPStatus.OK, [('Content-Length', str(len(body)))], body
        else:
            return http.HTTPStatus.NOT_FOUND, [], b''

    @staticmethod
    def process_origin(headers, origins):
        origin = websockets.WebSocketServerProtocol.process_origin(headers, origins)

        if origin:
            print('[*] wss connection from: %s' % origin)

        if not origin or not origin.endswith('.gov.tw') and \
                not origin.endswith('iccert.nhi.gov.tw:7777'):
            raise websockets.InvalidOrigin(origin)


        return origin

def connect_reader():
    try:
        return HealthInsuranceSmartcardClient()
    except:
        raise ServiceError(8013, 'Can not connect to smartcard reader')

def get_basic_data():
    with lock, connect_reader() as client:
        try:
            client.select_applet()
            data = list(client.get_basic()[:-1])
            data.append(client.get_hc_card_data().decode('ascii')[:1])
            return ','.join(data)
        except SmartcardCommandException as e:
            raise
        except:
            raise ServiceError(8011, 'Failed to read basic data from smartcard')

def get_basic_data_encrypted(password):
    # Yes, password was not used to encrypt the data!
    # maybe we should remove the password argument and rename it to encoded?
    blob = get_basic_data().encode('big5-hkscs')
    return basic_encrypt(blob).hex().upper()

async def handler(ws, path):
    try:
        while True:
            cmd = await ws.recv()
            log_censored = any(cmd.startswith(c) for c in CENSORED_COMMANDS)
            def censor_data(data, splitter='='):
                if log_censored:
                    data_list = data.split(splitter, maxsplit=1)
                    if len(data_list) == 1:
                        return data
                    else:
                        return data_list[0] + splitter + '...(censored)'
                return data
            logger.info('InCmd = {{{ %s }}}' % censor_data(cmd))
            prefix = ''

            try:
                if cmd == 'Exit':
                    exit()

                elif cmd == 'GetVersion':
                    ret = 'GetVersion:0001'

                elif cmd == 'GetBasic':
                    prefix = 'GetBasic:'
                    ret = get_basic_data()

                elif cmd == 'GetRandom':
                    rnd = int.from_bytes(os.urandom(8), 'little')
                    ret = str(rnd).zfill(16)[-16:]
                    assert len(ret) == 16
                    ret = 'GetRandom:%s' % ret

                elif cmd.startswith('EnCrypt?Pwd='):
                    prefix = 'EnCrypt:'
                    data = cmd.split('=', maxsplit=1)[1].encode('ascii')

                    if not (6 <= len(data) <= 12):
                        raise ServiceError(8009, 'Invalid password length (6 <= len <= 12)')

                    with lock, connect_reader() as client:
                        client.select_applet()
                        card_id = client.get_hc_card_id().decode('ascii')

                    encrypted = card_encrypt(data, card_id)
                    ret = encrypted.hex().upper()

                elif cmd.startswith('H_Sign?Random='):
                    prefix = 'H_Sign:'
                    data = cmd.split('=')[1].encode('ascii')
                    assert len(data) == 20 and data[:4] == b'0001'
                    sam_hc_auth_check(raise_on_failed=True)
                    with lock, connect_reader() as client:
                        sig = sam_hc_auth(client, data)
                    ret = sig.decode('ascii')

                elif cmd.startswith('SecureGetBasicWithParam?Pwd='):
                    prefix = 'SecureGetBasicWithParam:'
                    pwd = cmd.split('=', maxsplit=1)[0]
                    ret = get_basic_data_encrypted(pwd)

                else:
                    ret = '9999'
            except (SmartcardCommandException, ServiceError) as e:
                if isinstance(e.error_code, (int, str)):
                    prefix = ''
                    result = '%d' % e.error_code
                    logger.error('Error = {{{ %d: %s }}}' % (e.error_code, e.description))
                else:
                    result = '9876'
                    logger.error('Error = {{{ Unexpected Error -> %r }}}' % e)
            else:
                result = prefix + ret

            await ws.send(result)

            result = censor_data(result, ':')
            if len(result) >= 32:
                result = '%s...(%d bytes)' % (result[:32], len(result) - 32)
            logger.info('OutResult = {{{ %s }}}' % result)
    except websockets.ConnectionClosedOK:
        pass
    except websockets.ConnectionClosedError:
        pass

ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ssl_context.load_cert_chain('certs/chain.crt', 'certs/host.key')

import pysoxy

class PolyServer:
    def is_serving(self):
        return True

def forwarder(sock):
    # this function will be executed in new thread,
    # we need to create a new event loop
    event_loop = asyncio.new_event_loop()

    server = websockets.WebSocketServer(event_loop)
    server.wrap(PolyServer())

    _, conn = event_loop.run_until_complete(event_loop.connect_accepted_socket(lambda: HTTP(handler, server, host='localhost', port=7777, secure=True), sock, ssl=ssl_context))
    event_loop.run_until_complete(conn.wait_closed())

pysoxy.main(forwarder, HOST)

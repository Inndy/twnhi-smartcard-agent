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
import logging
import sys
from collections import namedtuple

from smartcard.System import readers as get_readers
from smartcard.util import toHexString

logging.basicConfig(level='INFO', stream=sys.stdout)
logger = logging.getLogger(__name__)

class SmartcardException(Exception):
    pass

class SmartcardCommandException(SmartcardException):
    def __init__(self, *args):
        super.__init__(*args)
        self.error_code = None
        self.description = None

class SmartcardClient:
    def __init__(self, conn=None):
        if conn is None:
            conn = select_reader_and_connect()

        if not conn:
            raise SmartcardException('Smartcard connection was not provided')
        self.conn = conn

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def close(self):
        if self.conn:
            self.conn.disconnect()

    def fire(self, cmd):
        data, a, b = self.conn.transmit(cmd)
        if (a, b) != (0x90, 0x00):
            raise SmartcardCommandException(data, (a, b))
        return bytes(data)

HCBasicData = namedtuple('HCBaseData', ['card_id', 'id', 'name', 'birth', 'gender', 'unknown'])

def error_info(error_code, description):
    def error_wrapper(f):
        def wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except SmartcardCommandException as e:
                e.error_code = error_code
                e.description = description
                raise
        return wrapper
    return error_wrapper

class HealthInsuranceSmartcardClient(SmartcardClient):
    @error_info(7004, 'Failed to select applet')
    def select_applet(self):
        logger.debug('select default applet')
        self.fire([
            0x00, 0xA4, 0x04, 0x00, 0x10, 0xD1, 0x58, 0x00,
            0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x11, 0x00
        ])

    def select_sam_applet(self):
        logger.debug('select sam applet')
        self.fire([
            0x00, 0xA4, 0x04, 0x00, 0x10, 0xD1, 0x58, 0x00,
            0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x31, 0x00
        ])

    @error_info(8011, 'Failed to get basic data')
    def get_basic(self):
        logger.debug('get basic data')
        data = self.fire([0, 0xca, 0x11, 0, 2, 0, 0, 0])
        return HCBasicData(
            data[:12].decode('ascii'),
            data[32:42].decode('ascii'),
            data[12:32].rstrip(b'\0').decode('big5-hkscs'),
            data[42:49].decode('ascii'),
            data[49:50].decode('ascii'),
            data[50:].decode('ascii'),
        )

    @error_info(8010, 'Failed to get card data')
    def get_hc_card_data(self):
        logger.debug('get HC card data')
        return self.fire([0, 0xca, 0x24, 0, 2, 0, 0, 0])

    @error_info(8001, 'Failed to get card id')
    def get_hc_card_id(self):
        logger.debug('get HC card id')
        return self.fire([0, 0xca, 0, 0, 2, 0, 0, 0])

    @error_info(8002, 'Failed to get card random')
    def get_random(self):
        logger.debug('get random')
        return self.fire([0, 0x84, 0, 0, 8])

    @error_info(8006, 'Secure access module signing failed')
    def muauth_hc_dc_sam(self, data: bytes):
        logger.debug('muauth_hc_dc_sam')
        if len(data) > 32:
            raise ValueError('data size must be less than 33 bytes')

        prefix = [0x00, 0x82, 0x11, 0x12, 0x20]
        suffix = [0x10]

        payload = prefix + list(data.ljust(32, b'\0')) + suffix
        assert len(payload) == 0x26
        return self.fire(payload)

def select_reader_and_connect(interactive=False):
    readers = get_readers()

    if not readers:
        logger.error('Please connect your smartcard reader')
        return
    elif len(readers) == 1:
        logger.info('Only one reader connected, use that one: %s', readers[0])
        reader = readers[0]
    elif not interactive:
        logger.info('Non-interactive was used, select first reader')
        reader = readers[0]
    else:
        print('%d readers available, please select one:' % len(readers))
        for i, r in enumerate(readers):
            print('%-2d : %s' % (i, r))

        idx = int(input('\n  Reader number: '))
        reader = readers[idx]

    conn = reader.createConnection()
    conn.connect()
    return conn

if __name__ == '__main__':
    try:
        conn = select_reader_and_connect(True)
        if not conn:
            raise Exception('No reader connected or selection failed')
    except Exception as e:
        logger.exception('Can not connect to reader, error: %r', e)
        sys.exit(1)

    with HealthInsuranceSmartcardClient(conn) as client:
        client.select_applet()
        print(client.get_basic())

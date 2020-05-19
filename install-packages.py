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
import sys

from hashlib import sha256
from imp import reload
from io import BytesIO
from pprint import pprint
from urllib.request import urlopen
from zipfile import ZipFile

SWIG_LOCAL_FILENAME = 'swigwin-4.0.1.zip'
SIWG_ZIP_URL = 'http://prdownloads.sourceforge.net/swig/swigwin-4.0.1.zip'
SWIG_ZIP_HASH = '8c504241ad4fb4f8ba7828deaef1ea0b4972e86eb128b46cb75efabf19ab4745'

is_windows = os.name == 'nt'

def pyexec(*args, executable=sys.executable):
    return os.system('%s -m %s' % (executable, ' '.join(args)))

def which(fname):
    if is_windows:
        fname += '.exe'

    for p in os.getenv('PATH').split(os.path.pathsep):
        full = os.path.join(p, fname)
        if os.path.exists(full):
            return full

def check_version():
    if sys.version_info.major < 3 or \
            sys.version_info.minor < 6:
        print('[-] Python version not match: %s' % sys.version)
        exit()

def install_virtualenv():
    try:
        import virtualenv
        major_version = int(virtualenv.__version__.split('.')[0])
        if major_version >= 20:
            return
        else:
            print('[*] Upgrade virtualenv')
    except:
        pass

    ret = pyexec('pip', 'install', '-U', '--user', 'virtualenv')
    if ret:
        print('[-] Failed to execute pip')
        exit(1)

def load_virtualenv():
    if not os.path.exists('venv'):
        print('[*] Create new virtualenv')
        pyexec('virtualenv', '--copies', '--download', 'venv')

    print('[*] Activate venv in current interpreter')
    the_file = os.path.join('venv', 'Scripts', 'activate_this.py') \
            if is_windows else \
            os.path.join('venv', 'bin', 'activate_this.py')
    exec(open(the_file).read(), {'__file__': the_file})

def load_swig():
    if not is_windows:
        return

    if which('swig'):
        return

    if not os.path.exists(SWIG_LOCAL_FILENAME):
        print('[+] Downloading file from %s' % SIWG_ZIP_URL)
        response = urlopen(SIWG_ZIP_URL)
        data = response.read()

        with open(SWIG_LOCAL_FILENAME, 'wb') as fp:
            fp.write(data)
    else:
        print('[+] Use %s from local' % SWIG_LOCAL_FILENAME)
        with open(SWIG_LOCAL_FILENAME, 'rb') as fp:
            data = fp.read()

    print('[*] Check if file hash match %s' % SWIG_ZIP_HASH)
    assert sha256(data).hexdigest().lower() == SWIG_ZIP_HASH

    print('[*] Read zip file')
    zfile = ZipFile(BytesIO(data))
    pathname = zfile.infolist()[0].filename
    if os.path.exists(pathname):
        print('[+] Zip file already extracted')
    else:
        print('[+] Extracting files')
        zfile.extractall('.')

    path = os.getenv('PATH')
    swig_path = os.path.join(os.path.abspath('.'), 'swigwin-4.0.1')
    new_path = swig_path + os.path.pathsep + path
    os.putenv('PATH', new_path)
    print('New $PATH:')
    pprint(new_path.split(os.path.pathsep))

def install_dependencies():
    print('[*] Installing dependencies')
    ret = pyexec('pip', 'install', '-r', 'requirements.txt', executable='python')
    if ret:
        print('[-] Failed to install dependencies')
        exit(1)

def try_import_packages():
    try:
        import hexdump
        import websockets
        import Cryptodome
        import smartcard
    except ImportError as e:
        print('[-] Can not import one of dependencies: %s' % e.name)
        exit(1)

def finish():
    print('[!] We are good to go!')
    print('[*] Follow post-installation instructions to setup root certiciate and run the program')

if __name__ == '__main__':
    check_version()
    install_virtualenv()
    load_virtualenv()
    load_swig()
    install_dependencies()
    try_import_packages()
    finish()

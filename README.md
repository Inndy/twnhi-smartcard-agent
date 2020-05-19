# TWNHI Smartcard Agent

## 這是什麼？ / What is this?

這是一個可以取代
[健保卡讀卡機元件](https://cloudicweb.nhi.gov.tw/cloudic/system/SMC/mEventesting.htm)
的程式，使用 Python 重新撰寫，避開了原始實作的軟體缺陷，提供更好的品質與文件。

## TODO

- [x] 增加 socks5 proxy 伺服器，攔截 `iccert.nhi.gov.tw` 的連線 /
      Add socks5 proxy to hijack connection to `iccert.nhi.gov.tw`
- [ ] 完善文件 / Finish documents
- [x] 驗證 client 來自 `*.gov.tw` / Limit the connection was came from `*.gov.tw`
- [ ] 預編譯 `pyscard` 套件 / Prebuild `pyscard` package
- [ ] 製作 prebuilt package 並加入 GitHub releases /
      Prebuild package and add to GitHub releases
- [ ] 蒐集使用回饋 / Collect usage feedbacks

## 相依套件 / Dependencies

- `python>=3.6` (Only tested on Python 3.8.0)
- `openssl>=1.1`
- `virtualenv`
- `requirements.txt` 檔案內列出的 Python 套件
- Windows 使用者需要 Visual Studio 或者
  [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)

## 我很懶，給我懶人包 / TL;DR
```
# Windows (PowerShell)
> Set-ExecutionPolicy -ExecutionPolicy Unrestricted -Scope Process -Force
> python.exe install-packages.py
> .\venv\Scripts\activate.ps1
> python.exe server.py

# Linux (Ubuntu)
$ sudo apt-get install libpcsclite-dev

# Linux and macOS
$ brew install swig # homebrew/linuxbrew
$ python3 install-packages.py
$ source ./venv/bin/activate
$ python3 server.py
```

## 安裝方式 / Setup

### 範例指令格式 / Note for the commands listed below
```
> python.exe --version # this command is for Windows
$ python3 --version    # this command is for Linux and macOS
```

### 確認 Python 版本大於等於 3.6 / Check python version
```
> python.exe --version
$ python3 --version
Python 3.8.0
```

### 確認有沒有安裝好 virtualenv / Check virtualenv
```
> python.exe -m virtualenv
$ python3 -m virtualenv
python3: No module named virtualenv
```

### 安裝 virtualenv / Install virtualenv
```
> python.exe -m pip install virutalenv
$ python3 -m pip install virutalenv
(很長的安裝畫面... / Installation progress...)
```

### 確認有沒有安裝好 virtualenv / Check virtualenv again
```
> python.exe -m virutalenv
$ python3 -m virtualenv
usage: virtualenv [--version] [--with-traceback] [-v | -q] [--app-data APP_DATA] [--clear-app-data]
                  [--discovery {builtin}] [-p py] [--creator {builtin,cpython3-win,venv}]
				  [--seeder {app-data,pip}] [--no-seed] [--activators comma_sep_list] [--clear]
				  [--system-site-packages] [--symlinks | --copies] [--no-download | --download]
				  [--extra-search-dir d [d ...]] [--pip version] [--setuptools version]
				  [--wheel version] [--no-pip] [--no-setuptools] [--no-wheel] [--symlink-app-data]
				  [--prompt prompt] [-h]
				  dest
virtualenv: error: the following arguments are required: dest
```

### 建立一個 virtualenv / Create a virtualenv
```
> python.exe -m virtualenv venv
$ python3 -m virtualenv venv
created virtual environment CPython3.6.8.final.0-64 in 3169ms
  creator CPython3Posix(dest=/code/venv, clear=False, global=False)
  seeder FromAppData(download=False, pip=latest, setuptools=latest, wheel=latest, via=copy, app_data_dir=/home/user/.local/share/virtualenv/seed-app-data/v1.0.1)
  activators BashActivator,CShellActivator,FishActivator,PowerShellActivator,PythonActivator,XonshActivator
```

### 啟動 virtualenv / Activate virtualenv we just created
```
> .\venv\Scripts\activate.ps1 # Windows with Powershell
$ source ./venv/bin/activate # Linux and macOS, I assume you are using a POSIX shell
```

#### PowerShell 錯誤 / PowerShell Error

PowerShell 預設不允許執行不信任的 script，如果你發生以下錯誤，請執行
`Set-ExecutionPolicy -ExecutionPolicy Unrestricted -Scope Process -Force`
，這將會允許現在的 PowerShell process 執行外部 script

Default config of PowerShell does not allow external script execution.
Execute `Set-ExecutionPolicy -ExecutionPolicy Unrestricted -Scope Process -Force`
to temporarily allow execution of external script.

```
PS C:\code> .\venv\Scripts\activate.ps1
.\venv\Scripts\activate.ps1 : 因為這個系統上已停用指令碼執行，所以無法載入 C:\code\venv\Scripts\activate.ps1 檔案。如需詳細資訊，請參閱 about_Execution_Policies，網址為 https:/go.microsoft.com/fwl
ink/?LinkID=135170。
位於 線路:1 字元:1
+ .\venv\Scripts\activate.ps1
+ ~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : SecurityError: (:) [], PSSecurityException
    + FullyQualifiedErrorId : UnauthorizedAccess
PS C:\code> Set-ExecutionPolicy -ExecutionPolicy Unrestricted -Scope Process -Force
PS C:\code> .\venv\Scripts\activate.ps1
(venv) PS C:\code>
```

### 安裝 Swig / Install Swig
[pyscard](https://github.com/LudovicRousseau/pyscard/blob/master/INSTALL.md#installing-on-gnulinux-or-macos-from-the-source-distribution)
需要使用到 [Swig](http://www.swig.org/) 來產生 Python native extension

macOS 使用者推薦使用 [Homebrew](https://brew.sh/) 來安裝套件，Linux 使用者也可以 Homebrew
([Linuxbrew 目前已經與 Homebrew 合併](https://github.com/Linuxbrew/brew/issues/612))，
使用發行版自帶的套件管理工具 (apt, rpm, pacman... etc.) 來安裝 swig。
```
$ brew install swig # Use homebrew/linuxbrew to install swig
```

### 安裝需要的套件 / Install python packages
```
$ sudo apt-get install libpcsclite-dev # Linux need libpcsclite-dev, apt-get is for Ubuntu
$ pip install -r requirements.txt
```


## 使用方式 / Usage

1. 啟動 virtualenv / Activate the virtualenv
2. 執行 server.py / Run server.py
3. 設定瀏覽器使用 socks5 proxy 127.0.0.1:17777 /
   Config your browser to use 127.0.0.1:17777 as socks5 proxy

### 設定瀏覽器使用 socks5 proxy / Config your browser to use socks5 proxy

#### Chrome

- [Proxy SwitchyOmega](https://chrome.google.com/webstore/detail/proxy-switchyomega/padekgcemlokbadohgkifijomclgjgif)
- [FoxyProxy Standard](https://chrome.google.com/webstore/detail/foxyproxy-standard/gcknhkkoolaabfmlnjonogaaifnjlfnp)

See [How to setup socks5 proxy in Chrome with FoxyProxy](docs/setup-socks5-proxy-chrome-foxyproxy.md)

#### Firefox

> TBD

### 設定系統信任 root certificate / Config your system to trust our root certificate

#### Windows
```
> cd certs
> .\trust_ca.cmd
```

#### macOS
```
$ cd certs
$ ./trust_ca_macos.sh
```

### Linux
```
# For Ubuntu and Firefox
$ sudo apt-get install libnss3-tools
$ cd certs
$ ./trust_ca_ubuntu_firefox.sh
```

關閉瀏覽器，再重新開啟設定才會生效

### 啟動伺服器並進行測試
```
> python server.py
```

設定好 socks5 porxy，並且用瀏覽器開啟
[https://iccert.nhi.gov.tw:7777/](https://iccert.nhi.gov.tw:7777/)

正確設定的狀況下應該不會看到任何錯誤，並且看到 `It works!` 就表示 agent 啟動成功

## 資訊安全考量 / Security Issue

### 自簽憑證 / Self-signed Certificate

由於健保卡讀卡機元件使用 wss (WebSocket Secure) 通訊協定，因此必須要有 SSL/TLS 憑證，
目前健保署並未提供 `iccert.nhi.gov.tw` 的有效憑證，因此我們使用自簽憑證來處理這個問題。

為了使用方便，安裝步驟中會引導使用者在系統上安裝並信任自簽根憑證，為了使用者的方便，
已經有一組預先產生好的憑證可以使用，為了確保該憑證不會被濫用，我們已將根憑證的私鑰銷毀。

若您希望有更高的安全性，可以參考 certs 目錄底下的 Makefile，裡面有使用 openssl
重新產生一組私鑰與憑證的方法，自行產生自己的根憑證與網站憑證，
再銷毀根憑證的私鑰來保證自簽根憑證不會遭到竊取與盜用。

以下是重新產生憑證的步驟：

```
> cd certs
> make clean
> make all
# 現在可以參考上面的步驟，讓系統信任剛剛產生的 CA
> ./trust_ca_macos.sh # 以 macOS 為例
```

## 授權 / License

[GPL v3](LICENSE)

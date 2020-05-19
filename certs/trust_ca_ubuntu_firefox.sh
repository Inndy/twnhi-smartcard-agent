#!/bin/bash

if [ ! -x "$(which certutil 2>&-)" ]
then
	echo "[-] Install libnss3-tools first"
fi

for f in ~/.mozilla/firefox/*.default*/cert9.db
do
	echo --------------------------------------------------------------------------------
	echo $f
	certutil -d "${f%/*}" -A -i ca.crt -n 'Inndys NHI Smartcard Client' -t C
	certutil -d "${f%/*}" -L
done

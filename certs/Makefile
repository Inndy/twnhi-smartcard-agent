DAYS ?= 730

all: host.crt check chain.crt

clean:
	rm ca.key ca.crt host.key host.crt host.csr chain.crt

finalize: host.crt
	rm ca.key
	rm chain.crt
	$(MAKE) chain.crt
	: Now you can trust ca.crt in your system, and nobody can abuse this root CA

ca.key:
	openssl genrsa -out ca.key 4096

ca.crt: ca.key
	openssl req -x509 -new -nodes -key ca.key -sha256 -days $(DAYS) -out ca.crt -subj "/C=TW/ST=Taiwan/O=Inndy's NHI Smartcard Client"

host.key:
	openssl genrsa -out host.key 4096

host.csr: host.key
	openssl req -new -key host.key -config san.cnf -sha256 -out host.csr

host.crt: host.csr ca.crt ca.key
	openssl x509 -req -in host.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out host.crt -days $(DAYS) -sha256 -extensions req_ext -extfile san.cnf

chain.crt:
	cat host.crt ca.crt > chain.crt

check:
	: ==================== ca.crt ====================
	openssl x509 -noout -text -in ca.crt
	: ==================== host.crt ====================
	openssl x509 -noout -text -in host.crt

#!/bin/sh

security add-trusted-cert -r trustRoot -k ~/Library/Keychains/login.keychain-db ca.crt

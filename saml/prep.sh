#!/usr/bin/env bash

rm -rf resources/certs
mkdir -p resources/certs
openssl req -new -newkey rsa:2048 -days 3650 -nodes -x509 -subj "/CN=apps,OU=iam,DC=home,DC=local" -keyout resources/certs/keycloakapps.key -out resources/certs/keycloakapps.crt
openssl req -new -newkey rsa:2048 -days 3650 -nodes -x509 -subj "/CN=splunksaml,OU=iam,DC=home,DC=local" -keyout resources/certs/splunksaml.key -out resources/certs/splunksaml.crt
cat resources/certs/splunksaml.crt resources/certs/splunksaml.key >  resources/splunk/system/local/splunksaml.pem
cp resources/certs/keycloakapps.crt resources/splunk/system/local/idpCerts

SPLUNKSAMLCERTIFICATE=$(openssl x509 -in resources/certs/splunksaml.crt -outform der | base64 -w 0)
APPSCERTIFICATE=$(awk '{printf("%s\\\\n",$0)}' resources/certs/keycloakapps.crt)
APPSPRIVATEKEY=$(awk '{printf("%s\\\\n",$0)}' resources/certs/keycloakapps.key)
sed -e "s@{{SPLUNKSAMLCERTIFICATE\}}@$SPLUNKSAMLCERTIFICATE@" -e "s@{{APPSCERTIFICATE}}@$APPSCERTIFICATE@" -e "s@{{APPSPRIVATEKEY}}@$APPSPRIVATEKEY@" resources/realms/apps.template > resources/realms/apps.json


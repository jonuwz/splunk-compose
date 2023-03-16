#!/bin/bash
USER=${1?Specify splunk user}
token=$(curl -s --fail -k -u admin:password -X POST https://localhost:8089/services/authorization/tokens?output_mode=json -d name=${USER} -d type=static --data-urlencode expires_on=+10y -d audience=user | jq -r '.entry[0].content.token')

cd certs

sed -i "/$USER/d" splunk_tokens/lookup
echo "$USER $token" >> splunk_tokens/lookup


[[ -e $USER.p12 ]] && exit 1

keytool -genkeypair -alias ${USER} -storetype PKCS12 -keyalg RSA -keysize 2048 -keystore ca.p12 -dname "CN=${USER}" -storepass password -keypass password
keytool -certreq -keystore ca.p12 -storetype PKCS12 -storepass password -alias ${USER} -file ${USER}.csr
keytool -gencert -keystore ca.p12 -storetype PKCS12 -storepass password -alias ca -infile ${USER}.csr -outfile ${USER}.cer
keytool -importcert -keystore ca.p12 -storetype PKCS12 -storepass password -file ${USER}.cer -alias ${USER}
keytool -importkeystore -srckeystore ca.p12 -destkeystore ${USER}.p12  -deststoretype PKCS12 -srcalias ${USER} -deststorepass password -destkeypass password -srcstorepass password

rm ${USER}.{cer,csr}


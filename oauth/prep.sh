
[[ -d certs ]] && rm -rf certs

mkdir -p certs
(
cd certs

# CA
keytool -genkeypair -alias ca -storetype PKCS12 -keyalg RSA -keysize 2048 -keystore ca.p12 -dname "CN=CA" -storepass password -keypass password -ext bc=ca:true

# https keystore - SSL certs for keycloak
keytool -genkeypair -alias okeycloak -storetype PKCS12 -keyalg RSA -keysize 2048 -keystore ca.p12 -dname "CN=okeycloak" -storepass password -keypass password
keytool -certreq -keystore ca.p12 -storetype PKCS12 -storepass password -alias okeycloak -file okeycloak.csr
keytool -gencert -keystore ca.p12 -storetype PKCS12 -storepass password -alias ca -infile okeycloak.csr -outfile okeycloak.cer -ext "SAN:c=DNS:localhost,DNS:okeycloak,IP:127.0.0.1"
keytool -importcert -keystore ca.p12 -storetype PKCS12 -storepass password -file okeycloak.cer -alias okeycloak
keytool -storepass password -exportcert -keystore ca.p12 -alias ca | openssl x509 -inform der -out ca.crt
keytool -importkeystore -srckeystore ca.p12 -destkeystore keystore.p12  -deststoretype PKCS12 -srcalias okeycloak -deststorepass password -destkeypass password -srcstorepass password

# truststore - list the CA that keycloak will trust for client certs
keytool -import -trustcacerts -file ca.crt -alias ca -keystore truststore.p12 -storetype PKCS12 -noprompt -storepass password

# cleanup
rm -f *.cer *.csr 

# JWT signing cert
openssl req -new -newkey rsa:2048 -days 365 -nodes -x509 -subj /CN=api -keyout jwt.key -out jwt.crt
openssl rsa -in jwt.key -pubout > jwt.pub
mkdir splunk_tokens
touch splunk_tokens/lookup
)

JWTPRIVATE=$(openssl pkey -in certs/jwt.key -outform der | base64 -w 0)
JWTCERTIFICATE=$(openssl x509 -in certs/jwt.crt -outform der | base64 -w0) # confusing - expect this to be the public key - but you need to generate a certificate ? I guess it could be used for other things.

sed -e "s@{{JWTPRIVATE}}@$JWTPRIVATE@" -e "s@{{JWTCERTIFICATE}}@$JWTCERTIFICATE@" resources/realms/api.template > resources/realms/api.json

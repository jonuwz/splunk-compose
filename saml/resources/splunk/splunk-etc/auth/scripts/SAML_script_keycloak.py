from commonAuth import *
logger = getLogger(f"{logPath}/splunk_scripted_authentication_keycloak.log", "keycloak")

if sys.version_info < (3,0):
    logger.error("Python 2 has been deprecated. Use Python 3 to execute this script instead.")

import requests
import json
from urllib.parse import quote

# In Splunk Web UI under Authentication Extensions > Script Secure Arguments:
# key = baseUrl, value = <baseUrl for keycloak>
# key = realm, value = <name of realm>
# key = client, value = <client i.e. splunk>
# key = keycloakUsername
# key = keycloakPassword

request_timeout = 10
errMsg = ""

def getToken(url,username,password):
    resp = requests.post(url,data={"username": username, "password": password,"grant_type": "password", "client_id": "admin-cli"})
    return resp.json()['access_token']


def getClientId(session,url,client):
  data = session.get(url,timeout=request_timeout).json()
  clients = [ c['id'] for c in data if c.get('clientId','') == client ]
  return clients[0]

def getUserInfo(args):
    username = args['username']

    if not username:
        errMsg = "Username is empty. Not executing API call"
        logger.error(errMsg)
        return FAILED + " " + ERROR_MSG + errMsg
    logger.info(f"Running getUserInfo() for username={username}")

    # Extracting base url and API key from authentication.conf under scriptSecureArguments
    BASE_URL = KEYCLOAK_USERNAME = KEYCLOAK_PASSWORD = REALM = CLIENT = ""

    try:
      BASE_URL = args['idpURL']
      KEYCLOAK_USERNAME = args['idpUsername']
      KEYCLOAK_PASSWORD = args['idpPassword']
      REALM = args['idpRealm']
      CLIENT = args['idpClient']
    except Exception as e:
      errMsg = "Not all scriptSecureArguments present : need ipdUsername, idpPassword, idpURL, idpRealm, idpClient"
      print(errMsg)
      logger.error(errMsg)
      return FAILED + " " + ERROR_MSG + errMsg

    # create persistent connection
    token = getToken(f'{BASE_URL}/realms/master/protocol/openid-connect/token',KEYCLOAK_USERNAME,KEYCLOAK_PASSWORD)
    session = requests.Session()
    session.headers = {'Accept': 'application/json', 'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'}

    # get clientId - would be better to just shove this directly in serure input parameters
    CLIENT_ID = getClientId(session, f'{BASE_URL}/admin/realms/{REALM}/clients', CLIENT)

    usernameUrl = f'{BASE_URL}/admin/realms/{REALM}/users?username={username}&exact=true'
    usernameResponse = session.get(usernameUrl,timeout=request_timeout)

    if usernameResponse.status_code != 200:
        errMsg = f"Failed to get user info for username={username} with status={usernameResponse.status_code} and response={usernameResponse.text}"
        logger.error(errMsg)
        if usernameResponse.status_code == 401:
            errMsg = "It appears your username/password are incorrect. Check your keycloak details "
            logger.warning(errMsg)
        elif usernameResponse.status_code == 404:
            errMsg = f"The user you are querying (username={username}) does not exist"
            logger.error(errMsg)
        return FAILED + " " + ERROR_MSG + errMsg
    try:
        nameAttributes = json.loads(usernameResponse.text)
    except Exception as e:
        errMsg = f"Failed to parse user info for username={username} with error={str(e)}"
        logger.error(errMsg)
        return FAILED + " " + ERROR_MSG + errMsg

    if len(nameAttributes) > 1:
        errMsg = f"More than 1 match for username={username} got {json.dumps(nameAttributes)}"
        logger.error(errMsg)
        return FAILED + " " + ERROR_MSG + errMsg

    nameAttributes=nameAttributes[0]

    if 'id' not in nameAttributes:
        errMsg = f"Failed to parse user info for username={username}, 'id' not present in response output: {usernameResponse.text}"
        logger.error(errMsg)
        return FAILED + " " + ERROR_MSG + errMsg
    id = nameAttributes['id']

    logger.info(f"Successfully obtained user info for username={username}")

    rolesUrl = f'{BASE_URL}/admin/realms/{REALM}/users/{id}/role-mappings/clients/{CLIENT_ID}'
    rolesResponse = session.get(rolesUrl,timeout=request_timeout)

    if rolesResponse.status_code != 200:
        errMsg = f"Failed to get user roles for username={username} with status={rolesResponse.status_code} and response={rolesResponse.text}"
        logger.error(errMsg)
        if rolesResponse.status_code == 401:
            errMsg = "It appears your username/password are incorrect. Check your keycloak details "
            logger.warning(errMsg)
        elif rolesResponse.status_code == 404:
            errMsg = f"The user you are querying (username={username}) does not have client mappings for client {CLIENT}"
            logger.error(errMsg)
        return FAILED + " " + ERROR_MSG + errMsg
    try:
        rolesAttributes = json.loads(rolesResponse.text)
    except Exception as e:
        errMsg = f"Failed to parse role info for username={username} with error={str(e)}"
        logger.error(errMsg)
        return FAILED + " " + ERROR_MSG + errMsg

    logger.info(f"Successfully obtained role info for username={username}")

    encodeOutput = True # default to always encode unless specified in args
    if 'encodeOutput' in args and args['encodeOutput'].lower() == 'false':
        encodeOutput = False

    roleNames = [ urlsafe_b64encode_to_str(role['name']) for role in rolesAttributes] if encodeOutput else [ role['name'] for role in rolesAttributes ]
    roleString = ":".join(roleNames)

    realNameString = urlsafe_b64encode_to_str(nameAttributes['attributes']['fullName'][0]) if encodeOutput else nameAttributes['attributes']['fullName'][0]
    nameString = urlsafe_b64encode_to_str(username) if encodeOutput else username

    return f'{SUCCESS} --userInfo={nameString};{realNameString};{roleString} --encodedOutput={str(encodeOutput).lower()}'

if __name__ == "__main__":
    callName = sys.argv[1]
    dictIn = readInputs()
    if callName == "getUserInfo":
        response = getUserInfo(dictIn)
        print(response)

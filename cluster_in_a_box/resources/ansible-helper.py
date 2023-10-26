import yaml
import http.client
import socket
import os
import json
import sys

HOSTNAME = os.uname()[1]
DOCKER_SOCK = "/var/run/docker.sock"
CONTAINER_NAME = None
OUTPUT = "/tmp/defaults/default.yml"

class UnixHTTPConnection(http.client.HTTPConnection):
    def __init__(self, unix_socket, timeout=10):
        super().__init__('localhost', timeout=timeout)
        self.unix_socket = unix_socket

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(self.unix_socket)

assert os.path.exists(DOCKER_SOCK), f"Docker sock does not exist"
assert os.access(DOCKER_SOCK,os.W_OK), f"Docker sock is not writable"

try:
  conn = UnixHTTPConnection(DOCKER_SOCK)
  conn.request("GET", f"/containers/{HOSTNAME}/json")

  response = conn.getresponse()
  body = response.read().decode()
  conn.close()
  j = json.loads(body)
  CONTAINER_NAME = j["Name"][1:]
except Exception as e:
  print(f"Failed to get container name from docker socket: {e}",file=sys.stderr)
  exit(1)


conf = {
  "splunk": {
    "hostname": CONTAINER_NAME,
    "conf": [
      {
        "key": "server",
        "value": {
          "directory": "/opt/splunk/etc/system/local",
          "content": {
            "general": {
              "serverName": CONTAINER_NAME
            }
          }
        }
      }
    ]
  }
}

if not os.path.exists(os.path.dirname(OUTPUT)):
  os.makedirs(os.path.dirname(OUTPUT))

with open(OUTPUT, 'w') as df:
  yaml.dump(conf,df)

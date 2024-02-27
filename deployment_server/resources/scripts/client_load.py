#!/usr/bin/env python3
import requests, sys, time, os

iters = int(sys.argv[1]) if len(sys.argv) > 1 else 100


with open('/opt/splunkforwarder/var/log/splunk/splunkd.log') as log:
    for line in log:
        if 'Running phone uri=' in line:
            conn = line.split("/")[-1].strip()
            break

url = f"{os.environ['SPLUNK_DEPLOYMENT_SERVER']}:8089/services/broker/phonehome/{conn}"
headers = { 'Content-type': 'text/xml; charset=UTF-8' }
payload = '<messages><publish channel="deploymentServer/phoneHome/default">&lt;phonehome token="default"/&gt;</publish></messages>'

good=0
start=time.time()
first_iter_dur=0

for i in range(iters):
    its = time.time()
    resp = requests.post(url,headers=headers,data=payload)
    itd = time.time()-its
    if i == 0:
        first_iter_dur=itd
    if 'checksum' in resp.content.decode():
       good=good+1

dur=time.time()-start

print(f"{good} / {iters} in {dur:.3f}. 1st call {first_iter_dur:.3f} avg {dur/iters:.3f} connection: {conn}")

#!/usr/bin/env python3

import asyncio, aiohttp, re, random, sys
from uuid import UUID
from tqdm.asyncio import tqdm_asyncio

stub='http://localhost:8189/services/broker'
clients = int(sys.argv[1]) if len(sys.argv) > 1 else 1000   # how many clients to spoof
concurrent = int(sys.argv[2]) if len(sys.argv) > 2 else 10  # max connections from this script at a time

limit = asyncio.Semaphore(concurrent)  # limit the number of http calls
reg_limit = asyncio.Semaphore(concurrent)  # limit the number of http calls
ping_payload = '<?xml version="1.0" encoding="UTF-8"?><messages/>'
handshake_payload = '<?xml version="1.0" encoding="UTF-8"?><messages><publish channel="tenantService/handshake">&lt;handshake/&gt;</publish></messages>'
topic_payload = '<?xml version="1.0" encoding="UTF-8"?><messages><publish channel="deploymentServer/phoneHome/default">&lt;phonehome token="default"/&gt;</publish></messages>'

def phonehome_url(conn): return f"{stub}/phonehome/{conn}"

async def make_request(session, url, data=None):
  
    try:   
       async with limit, session.post(url, data=data, headers={ 'Content-type': 'text/xml; charset=UTF-8' }) as resp:
           # await asyncio.sleep(0.1) # prove hadshake is not single threaded
           return await resp.read()
    except:
        return b''

async def register(session, hostname, id):

    rnd = random.Random(hostname) # use hostname as seed
    uuid = UUID(int=rnd.getrandbits(128), version=4)   # determinitstic uuid based on hostname
    client_id, build_number = uuid, "de405f4a7979" # to make the connect_url string clearer

    connect_url = f"{stub}/connect/{client_id}/{hostname}/{build_number}/linux-x86_64/8089/9.0.4/{uuid}/universal_forwarder/{hostname}" # duplicate fields ?
    resp = await make_request(session, connect_url)
    try:
        conn = re.split(r'[<>]',resp.decode())[4] # lazy decoding of xml to get connection string
    except:
        return None
        
    tenant_subscribe_url = f"{stub}/channel/subscribe/{conn}/tenantService%2Fhandshake%2Freply%2F{hostname}%2F{uuid}"
    topic_subscribe_url = f"{stub}/channel/subscribe/{conn}/deploymentServer%2FphoneHome%2Fdefault%2Freply%2F{hostname}%2F{uuid}"

    await make_request(session, tenant_subscribe_url)
    await make_request(session, phonehome_url(conn), data=ping_payload)
    await make_request(session, phonehome_url(conn), data=handshake_payload)
    await make_request(session, topic_subscribe_url)
    await asyncio.sleep(1)
    return conn # we need the connection string to feed into the separate "get apps" loop

async def main():
    
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False), raise_for_status=True) as session:

        print(f"\nconcurrency={concurrent} clients={clients}\n\nclient registrations") # spam all the registrations at the same time. fast
        conns = await tqdm_asyncio.gather( *[register(session, f"host{tid}", tid) for tid in range(clients)] )
        conns = [ c for c in conns if c is not None ]

        if len(conns) == 0:
            print(f"\nAll registrations failed, is stub url correct ? : {stub}\n")
            return

        print(f"fetching apps for {len(conns)} successfully registered clients") # get apps for all clients. slow
        responses = await tqdm_asyncio.gather( *[make_request(session, phonehome_url(conn), data=topic_payload) for conn in conns] )

        print(f"\ncorrect data : {sum([ 1 if 'checksum' in r.decode() else 0 for r in responses  ])} / {len(conns)}\n") # should == clients
        print(responses[-1].decode())

if __name__ == "__main__":
    asyncio.run(main())

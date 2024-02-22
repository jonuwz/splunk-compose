#!/usr/bin/env python3

import asyncio, aiohttp, re, random, sys
from uuid import UUID
from tqdm.asyncio import tqdm_asyncio

clients = int(sys.argv[1]) if len(sys.argv) > 0 else 1000   # how many clients to spoof
concurrent = int(sys.argv[2]) if len(sys.argv) > 1 else 10  # max connections from this script at a time

limit = asyncio.Semaphore(concurrent)  # limit the number of http calls
stub='http://localhost:8080/services/broker'
ping_payload = '<?xml version="1.0" encoding="UTF-8"?><messages/>'
handshake_payload = '<?xml version="1.0" encoding="UTF-8"?><messages><publish channel="tenantService/handshake">&lt;handshake/&gt;</publish></messages>'
topic_payload = '<?xml version="1.0" encoding="UTF-8"?><messages><publish channel="deploymentServer/phoneHome/default">&lt;phonehome token="default"/&gt;</publish></messages>'

def phonehome_url(conn): return f"{stub}/phonehome/{conn}"

async def make_request(session, url, data=None):
   
   async with limit, session.post(url, data=data, headers={ 'Content-type': 'text/xml; charset=UTF-8' }) as resp:
        resp.raise_for_status()
        return await resp.read()

async def register(session, hostname):

    rnd = random.Random(hostname) # use hostname as seed
    uuid = UUID(int=rnd.getrandbits(128), version=4)   # determinitstic uuid based on hostname
    client_id, build_number = uuid, "de405f4a7979" # to make the connect_url string clearer

    connect_url = f"{stub}/connect/{client_id}/{hostname}/{build_number}/linux-x86_64/8089/9.0.4/{uuid}/universal_forwarder/{hostname}" # duplicate fields ?
    resp = await make_request(session, connect_url)
    conn = re.split(r'[<>]',resp.decode())[4] # lazy decoding of xml to get connection string
    
    tenant_subscribe_url = f"{stub}/channel/subscribe/{conn}/tenantService%2Fhandshake%2Freply%2F{hostname}%2F{uuid}"
    topic_subscribe_url = f"{stub}/channel/subscribe/{conn}/deploymentServer%2FphoneHome%2Fdefault%2Freply%2F{hostname}%2F{uuid}"

    await make_request(session, tenant_subscribe_url)
    await make_request(session, phonehome_url(conn), data=ping_payload)
    await make_request(session, phonehome_url(conn), data=handshake_payload)
    await make_request(session, topic_subscribe_url)

    return conn # we need the connection string to feed into the separate "get apps" loop

async def main():
    
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:

        print(f"\nserver={stub} concurrency={concurrent} clients={clients}\n\nclient registrations") # spam all the registrations at the same time. fast
        conns = await tqdm_asyncio.gather( *[register(session, f"host{tid}") for tid in range(clients)] )

        print("client query apps") # get apps for all clients. slow
        responses = await tqdm_asyncio.gather( *[make_request(session, phonehome_url(conn), data=topic_payload) for conn in conns] )

        print(f"\ncorrect data : {sum([ 1 if 'checksum' in r.decode() else 0 for r in responses  ])} / {clients}\n") # should == clients

if __name__ == "__main__":
    asyncio.run(main())

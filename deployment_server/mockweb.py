#!/usr/bin/env python3

# this exists to prove the load script works.
# if you run the load script with 
# ./load.py 100 2    # concurrency of 2
# ./load.py 100 10   # concurrency of 10
# then the 2nd call should by 5x faster

from aiohttp import web
import asyncio

# fictitious response that satisfies all expected responses.
response = """
<xml checksum=1234><connection>lala</connection>
""" 

async def handle(request):
    await asyncio.sleep(0.1) # 
    return web.Response(text=response)

app = web.Application()
app.add_routes([web.get('/{tail:.*}', handle),
                web.post('/{tail:.*}', handle)])

if __name__ == '__main__':
    web.run_app(app, host='127.0.0.1', port=8080)
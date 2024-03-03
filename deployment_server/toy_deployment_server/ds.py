#!/usr/bin/env python3 
# THIS IS A TOY IMPLEMENTATION OF THE DEPLOYMENT SERVER
# IT ONLY PROCESSES WHITELISTS.
# THERE NO MACHINE TYPES / BLACKLIST SUPPORT
#
# generate large serverclass.conf from resources/conf/gendsconf
# 
# test performance with load.py
#
# performance bottleneck is regex at scale.
# i.e. for a given client, which serverclasses should i include.
# if you have 1000 serverclasses with 1000 regexes each,
# thats 1M*num_properties regexes PER client
#
# the 1st time we see a client, and need to calculate with serverclasses are eligible
# this implementation is ~ 10x-40x faster dependant on serverclasses count
# subsequent connections from a known client are about 150x-1000x faster due to caching
#
# To go further, 
# 1. DONE have a routine for generating 'bundles' from the apps, storing checksums + whether it causes a restart
# 2. DONE include these details in the serverclasses dict
# 3. HALFBAKED use a real webserver to handle /deployemnt/streams (the downloads)
# 4. implement cache invalidation if the serverclasses / apps change
# 5. implement cache removal for agent checksums not seen in a long time and/or
#    if the properties change for a UUID
# 6. don't use python. Use something that can use more than 1 CPU.
# 7. HALFBAKED figure out what the IP is in the real connect string. 
#    are we looking up the ip of the other end of the connection,
#    or using x-forwarded-for ?
#    This IP is used for matching
# 8. DONE Figure out what the xml properties are in the phonehome responses (responses.py)

from aiohttp import web
import hashlib, json, re, configparser, os, tarfile, gzip, socket, logging
from responses import format_getapps_response, format_handshake_response
from io import BytesIO

logging.basicConfig(level=logging.INFO)

connect_properties = ["client_id","dns_name","build","os","port","version","uuid","type","hostname"]
check_properties = ["client_id","hostname","dns_name"]
apps_dir = '/opt/splunk/etc/deployment-apps'
bundle_dir = './var/run/tmp'

cache = {}
clients = {}
apps = {}

async def handle_d_cl(r): return web.Response(text=json.dumps(clients,indent=2))
async def handle_d_sc(r): return web.Response(text=json.dumps(serverclasses,default=lambda o: o.pattern, indent=2)) # hack to display compiled regex
async def handle_d_ap(r): return web.Response(text=json.dumps(apps,indent=2))

def get_serverclasses():
    config = configparser.ConfigParser()
    config.read('serverclass.conf')

    serverclasses = {}
    for section in config.sections():
        sp = section.split(":")
        if len(sp) == 2 and sp[0] == "serverClass":
            whitelists = sorted([ f"(?:{v.replace('*','.*')})" for (k,v) in config.items(section) if k.startswith('whitelist.') ])
            serverclasses[sp[1]] = { "apps": [], "whitelists": whitelists }
            # The optimization here is to compile a single regex for the entire serverclass
            # compiling a regex from a string every time is slow.
            serverclasses[sp[1]]["whitelist"] = re.compile("|".join(whitelists))
            # We could do better than this.
            # For the static entries, compile a trie - matching that will be extremely fast.
            # then fallback to a regex engine for the remaining whitelist entries with wildcards.


    for section in config.sections():
        sp = section.split(":")
        if len(sp) == 4 and sp[0] == "serverClass" and sp[2] == "app":
            serverclasses[sp[1]]["apps"].append(sp[3])

    return serverclasses

def should_include_serverclass(sc,cksum):
    props = list(set([ clients[cksum][p] for p in check_properties ]))
    for prop in props:
        if serverclasses[sc]["whitelist"].match(prop): # match against the precompiled serverclass whitelist regex
            return True
    return False

def phonehome_topic(connection):
    # for a given connect string, construct an object with matching scs and the apps.
    payload = {}

    for sc, obj in serverclasses.items():          # iterate over all serverclasses
        include = cache.get((connection,sc),None)  # have we checked this client agaist the sc before ?

        if include == None:                        # Nope - populate the cache
            include = should_include_serverclass(sc,connection)
            cache[(connection,sc)] = include
        
        if include == True:                        # this sc matches the client
            payload[sc] = {}
            for a in obj["apps"]:                  # grab all the apps in the serverclass
                if a in apps:                      # check this app exists in the apps we've created bundles for
                    payload[sc][a] = {"checksum": apps[a]["cksum"], "restart": False}    
                    # if you want to do whitelisting at the app level too
                    # this is where you would do it.
                    # you need a new cache and 'should_include_app' function
                
    return format_getapps_response(clients[connection]["hostname"],clients[connection]["client_id"],payload)

async def handle_connect(r):
    parts = r.path.split('/')[4:]
    remote_ip = r.remote

    try:
        remote_host = str(socket.gethostbyaddr(remote_ip)[0])
    except:
        remote_host = remote_ip

    properties = dict(map(lambda i,j : (i,j) , connect_properties, parts)) # create a dict with keys defined in connect_properties
    # This is the connection string sent to the client, and will be part of every request the client sends from now on.
    conn=f"connnection_{remote_ip}_{properties['port']}_{remote_host}_{properties['hostname']}_{properties['client_id']}"

    # cache the client properties using the conenction string as a a key
    clients[conn] = properties
    logging.info(f"connection: remote={remote_host} connection_string={conn}")
    resp = web.Response(text=f'<?xml version="1.0" encoding="UTF-8"?><msg status="ok">{conn}</msg>')
    resp.headers['Content-Type'] = 'text/xml; charset=UTF-8'
    return resp

async def handle_phonehome(r):
    # an existing connection string should exist in the cache, we should check for this.
    body = await r.read()
    body = body.decode()
    conn = r.path.split('/')[4]

    if not conn in clients:
        text = '<messages status="not_connected"/>'
        action = "not_connected"
    elif '<publish channel="deploymentServer' in body:
        text = phonehome_topic(conn)
        action = "get_apps"
    elif '<publish channel="tenantService/handshake' in body:
        text = format_handshake_response(clients[conn]["hostname"],clients[conn]["client_id"])
        action = "handshake"
    elif '<messages/>' in body:
        text = '<messages status="ok"/>'
        action = "ping"
    else:
        text = '<messages status="ok"/>'
        action = "unknown"

    logging.info(f"phonehome: connection={conn} action={action}")
    resp = web.Response(text=text)
    resp.headers['Content-Type'] = 'text/xml; charset=UTF-8'
    return resp
    
async def handle_subscribe(r):
    conn = r.path.split('/')[5]

    if not conn in clients:
        text = '<?xml version="1.0" encoding="UTF-8"?><msg status="not_connected" reason="not_connected"/>'
        action = "not_connected"
    elif 'tenantService' in r.path:
        text = '<?xml version="1.0" encoding="UTF-8"?><msg status="ok"/>'
        action = "tenantService"
    elif 'deploymentServer' in r.path:
        text = '<?xml version="1.0" encoding="UTF-8"?><msg status="ok"/>'
        action = "deploymentServer"
    else:
        text = '<?xml version="1.0" encoding="UTF-8"?><msg status="not_connected" reason="not_connected"/>'
        action = "unknown"

    logging.info(f"subscribe: connection={conn} action={action}")
    resp = web.Response(text=text)
    resp.headers['Content-Type'] = 'text/xml; charset=UTF-8'
    return resp

async def handle_stream(r):
    name = r.rel_url.query.get('name',None)
    await r.read()
    if name is None:
        return web.Response(text='')
    
    # we should really see if the client accepts gzip, and if not, return the uncompressed bundle
    # is this actually async ?
    _, _, app = name.split(':')  # tenant , serverclass, app
    with open(apps[app]['loc'],'rb') as cf:
        content=cf.read() # in the real world you'd chunk this

    response = web.StreamResponse()
    response.enable_compression(force=False) # files are already compressed
    response.headers['Content-Type'] = 'octet-stream'
    response.headers['File-Name'] = f"{app}.bundle"
    response.headers['Content-Encoding'] = 'gzip'
    response.headers['Content-Length'] = str(len(content))

    await response.prepare(r)
    await response.write(content)
    await response.write_eof()

    return response

def prep_apps():

    if not os.path.exists(bundle_dir):
        os.makedirs(bundle_dir)

    # tarfiles contain the dates of the files.
    # the checksum of the tar file will change if any of the files
    # in it have their dates changed.
    # set the time of all the files to 0
    def notimes(tarinfo):
        tarinfo.mtime = 0
        return tarinfo

    # create a tgz for each app
    # if you look in a real bundle created by a real ds, you get
    # default/app.conf
    # i.e. no leading path elements, and no directories, only the files
    for app in [ f.path for f in os.scandir(apps_dir) if f.is_dir() ]:
        appname = os.path.basename(app)
        dest = f"{bundle_dir}/{appname}.bundle.gz"

        has_local_app = False 
        with tarfile.open(dest,"w:gz") as tf:

            for root, _, files in os.walk(app):
                for file in files:
                    fpath=f"{root}/{file}"
                    arcname = fpath[len(app)+1:]
                    if arcname == 'local/app.conf':
                        has_local_app = True
                    tf.add(fpath,arcname=arcname,filter=notimes)

            if not has_local_app: # create a local/app.conf if it doesnt exists
                tarinfo = tarfile.TarInfo(name='local/app.conf')
                tarinfo.uid = os.getuid()
                tarinfo.gid = os.getgid()
                tf.addfile(tarinfo=tarinfo, fileobj=BytesIO('# Autogenerated File'.encode()))

        # now we calculate the checksum of the tarfile, not the gz
        # the checksum advertised by the DS is the 1st 64 bits if the digest, converted to decimal
        # why ? who knows. maybe to fit in a LONG            
        with gzip.open(dest,'rb') as gf:
            content = gf.read()
            md5sum = hashlib.md5(content).hexdigest()
            # and now for something completely different

            cksum = int(md5sum[0:16],16)
        
        # cache the location of the gz and the checksum
        apps[appname] = { "loc": dest, "cksum": cksum}

app = web.Application()

app.add_routes([
    web.post('/services/broker/connect/{tail:.*}', handle_connect),
    web.post('/services/broker/phonehome/{tail:.*}', handle_phonehome),
    web.post('/services/broker/channel/subscribe/{tail:.*}', handle_subscribe),
    web.post('/services/streams/deployment',handle_stream),
    web.get('/debug/clients', handle_d_cl),
    web.get('/debug/serverclasses', handle_d_sc),
    web.get('/debug/apps', handle_d_ap)
])

if __name__ == '__main__':
    logging.info("Prepping apps")
    prep_apps()
    global serverclasses
    serverclasses = get_serverclasses()
    web.run_app(app, host='0.0.0.0', port=8080)

# Deployment Server
The creates a 4 node deployment server using splunk 9.2.0.1.  
  
Used for testing large deployments.

## Requirements

#### Software
Tested on ubuntu 22.04.  
  
You need the following modifications in sysctls :
```bash
# arp caches
net.ipv4.neigh.default.gc_thresh1 = 4096
net.ipv4.neigh.default.gc_thresh2 = 8192
net.ipv4.neigh.default.gc_thresh3 = 16384
# limit on number of files a process can have open
fs.nr_open = 1073741816
```
and the following increase in ulimits
```bash
root hard nofile 1073741816
```

You also need docker installed as per https://docs.docker.com/engine/install/ubuntu  
  
Not a requirement, but something to be aware of, You can only have 1023 devices attached to a network bridge.  
So if you need more than 1000 forwarders, you need to split the containers over multiple networks.  
This is handled in this repository.  

#### Hardware
Approximately 64GB ram per 1000 forwarders.  
Very fast storage if you plan to use swap.  

## Running
This will create 
* a standalone splunk server to index the logs (exposed on port 8000)
* 4 deployment servers, 8000 is mapped to a random ephemeral port
* a load balancer listening on port 8089, with source IP based load balancing to the 4 deployment servers
* 5 universal forwarders, 1 in each of the 5 client networks (dn0-4)
```bash
docker up -d
```

#### Adding more forwarders
There is a helper scrint called that adds universal forwarders, 50 at a time, spread over the 5 client networks until the target number is reached.  
```bash
./spinner 1000
```
You can not use this script and just set the number of replicas.  
This will attempt to start all forwarders at the same time, and this is very hard on I/O.  

#### Adding heavy deployment server configuration
Exec into 1 of the 4 deployemnt servers
```bash
docker exec -it d-sddbe-1 bash
/opt/scripts/gendsconf --apps 5000 --classes 5000 --regex 30 --appsperclass 5 > /opt/splunk/etc/system/local/serverclass.conf
```

This will create 5000 applications, and a serverclass.conf with
* 5000 classes
* 30 regular expressions per serverclass that will never match
* 5 apps allocated to each serverclass
* a serverclass called 'big' with 5 apps, and a single regex that will match all clients.

reload the configuratiion
```bash
curl -u admin:password -k https://localhost:80889/servicesNS/-/system/deployemnt/server/config/_reload
```
Go get a coffee.

##### Notes
* The deployment server will generate a directory with gz files for each serverclass, you can track progress with
```bash
tail -f /opt/splunk/var/log/splunk/splunkd.log | grep "g server"
```
* If restarted, the deployment server will not respond, and the ui will not be available until this process finishes
* track overall progress with `top` on the host.

## Observations
You can modify the docker compose configuration, such that there is a single deployment server doing all the work.  
When you do this there are problems when the number of regular expressions exceeds ~ 120K.  
You will observe that the deployemnt server 'leaks' sockets.  
```bash
ss -te4 | grep CLOSE | wc -l
```
connections in a close wait state are 'zombies'.  
The other end of the TCP connection (the UF) has closed its end.  
The OS on the DS is waiting for the splunk process to close its end too.  
This never happens.  
  
Observe tcp connections that are older than 2 minutes
```bash
find /proc/<PID of main splunk process>/fd -maxdepth 1 -mmin +2 -ls
```

If you want to find out what these are, take the socket number, then run
```bash
ss -te4 | grep <socket_number>
```
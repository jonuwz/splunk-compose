# Requirements
place the tgz for splunk 9.2.0.1 in images/deployment_Server  
place the tgz for universal forwarder 9.0.4 in images/universal_forwarder

# Running
```bash
docker compose -f debug-compose.yaml up sds sdd -d
```
This will create a deployment server listening on port 8010.  
This will create a standalone splunk mahcine for indexing on port 8000.  

The deployment server will have a serverclas.conf with 200K regular expressions.  
Yes this is absurd, but it makes performance testing more obvious.  

Wait until you can connect to the deployment server over the UI.  

Now start the clients
```bash
docker compose -f debug-compose.yaml up sdf0 sdf1 sdf2 sdf3 sdf4 -d
```

# Validation
connect to :8010 and login with admin/password.  
wait till you see 5 connected clients.  

# testing

## single client

```bash
time docker exec d-sdf0-1 /opt/scripts/client_load.py 10
```

This will grab the connection string from splunkd.log and publish to the deploymentServer/phoneHome/default channel.  
i.e. this is the bit that the deploymentclient does every phoneHomeInterval to look for apps.  
It will phone home 10 times, and print the timings.  

```bash
10 / 10 in 2.280. 1st call 0.249 avg 0.228 connection: connection_172.22.0.2_8089_d-sdf0-1.d_dn0_a4f05fdf1d67_F5F741C6-838F-468C-A4AA-A34B7702B57D

real    0m2.422s
user    0m0.007s
sys     0m0.007s
```  
  
Note that there is no speedup. Each call is just as slow as the first.  
This is the same result as allowing the clients to reach steady state, then running
```bash
index=_internal sourcetype=splunkd_access uri_path=/services/broker/* bytes>500| bin_time span=1m | xyseries _time uri_path spent
```


## multiple clients
```bash
time ( for i in {0..4};do (docker exec d-sdf${i}-1 python3 /opt/scripts/client_load.py 10 ) &done ;wait )
```
This will concurrently run the script on 5 deployment clients.  

If there's any parallelism at all, this should take < 5*the time for a single client.

```bash
10 / 10 in 10.270. 1st call 0.382 avg 1.027 connection: connection_172.21.0.2_8089_d-sdf4-1.d_dn4_3eafea1e85d0_9D99D8D7-ADFB-4C53-9980-C1D77F800E3D
10 / 10 in 10.507. 1st call 0.629 avg 1.051 connection: connection_172.24.0.2_8089_d-sdf1-1.d_dn1_51a43869cdaf_25E94239-1F6B-40AD-8E25-6C4D0DB0C17F
10 / 10 in 10.725. 1st call 0.848 avg 1.072 connection: connection_172.22.0.2_8089_d-sdf0-1.d_dn0_a4f05fdf1d67_F5F741C6-838F-468C-A4AA-A34B7702B57D
10 / 10 in 10.936. 1st call 1.072 avg 1.094 connection: connection_172.19.0.2_8089_d-sdf2-1.d_dn2_c5b2677b1dcd_DD848CCA-627F-4995-8B47-3F782E06FBA0
10 / 10 in 11.138. 1st call 1.275 avg 1.114 connection: connection_172.20.0.2_8089_d-sdf3-1.d_dn3_916d479a9789_E52CBB92-D57C-4ED6-94F8-2C5EF7B4D0EC

real    0m11.294s
user    0m0.021s
sys     0m0.055s
```

Not really

## Simulated load.
```bash
./load.py 100 100
```

This will simulate as well as i know how, 100 'new' hosts, register them fully, then publish to the deploymentServer/phoneHome/default channel.  
The publishing does 100 concurrently.  

if you now run

```bash
index=_internal sourcetype=splunkd_access uri_path=/services/broker/phonehome/* bytes>500 host* 
| stats latest(spent) as spent by uri_path 
| sort 0 - spent 
| eventstats min(spent) as fastest_request 
| eval order = round(spent/fastest_request)
```

it should be obvious that the deploment server accepts all the connections, then processes them sequentially.  



## spluk sso reverse-proxy example 

* connect to localhost:9000
* you'll be prompted for auth
* use splunkadmin/password or splunkuser/password

## Problems
* If your docker doesnt allocate IPs in the 172/8 range - you'll need to modify splunk-etc/system/local/web.conf
* Goto localhost:9000/debug/sso to see what the splunk instance is getting from the proxy

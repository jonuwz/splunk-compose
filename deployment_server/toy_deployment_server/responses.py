import socket

def format_getapps_response(hostname,client_id,items={}):

    rbit = []
    for sc in items:
        rbit.append( f'<serverClass name="{sc}">' )
        for app in items[sc]:
            cksum = items[sc][app]["checksum"]
            restart = "true" if items[sc][app]["restart"] else "false"
            rbit.append( f'<app name="{app}" checksum="{cksum}" restartSplunkd="{restart}"/>')
        rbit.append( f'</serverClass>' )

    text_parts = [
        '<messages status="ok">',
        f'<message connectionId="connection_127.0.0.1_8089_{socket.gethostname()}_direct_ds_default" hostname="direct" ipAddress="127.0.0.1" connName="ds_default" channel="deploymentServer/phoneHome/default/reply/{hostname}/{client_id}">',
        "".join([
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<deployResponse restartSplunkd="false" restartSplunkWeb="false" stateOnClient="enabled" issueReload="false" repositoryLocation="$SPLUNK_HOME/etc/apps" endpoint="$deploymentServerUri$/services/streams/deployment?name=$tenantName$:$serverClassName$:$appName$">',
            "".join(rbit),
            '</deployResponse>',
        ]).replace("<","&lt;").replace(">","&gt;"),
        '</message>',
        '</messages>'
    ]

    text = "".join(text_parts)
    return text

def format_handshake_response(hostname,client_id):

    text_parts = [ 
        '<messages status="ok">',
        f'<message connectionId="connection_127.0.0.1_8089_{socket.gethostname()}_direct_tenantService" hostname="direct" ipAddress="127.0.0.1" connName="tenantService" channel="tenantService/handshake/reply/{hostname}/{client_id}">',
        "".join([
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<tenancy>',
            '<status>ok</status>',
            '<tenantId>default</tenantId>',
            '<phoneHomeTopic>deploymentServer/phoneHome/default</phoneHomeTopic>',
            '<token>default</token>',
            '</tenancy>'
        ]).replace("<","&lt;").replace(">","&gt;"),
        '</message>',
        '</messages>'
    ]

    text = "".join(text_parts)
    return text
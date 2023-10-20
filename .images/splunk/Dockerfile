ARG VERSION=8.2.0
ARG TOOL=splunk
FROM splunk/${TOOL}:${VERSION}


USER root

# Do this 1st - it takes the longest
RUN sed -i 's/41812/1000/g' /etc/passwd && \
    sed -i 's/41812/1000/g' /etc/group && \
    chown -R 1000:1000 /home/splunk /opt/splunk* 

RUN update-ca-trust && \
    microdnf install -y vim git-core jq nmap net-tools lsof java-11-openjdk-headless && \
    microdnf clean all

RUN curl -s -L -f -o /tmp/tcpdump.rpm http://mirror.centos.org/centos/8-stream/AppStream/x86_64/os/Packages/tcpdump-4.9.3-1.el8.x86_64.rpm && \
    rpm -i /tmp/tcpdump.rpm && \
    rm /tmp/tcpdump.rpm

ADD ./refresh /usr/bin/refresh
ADD ./web.conf /tmp/web.conf
RUN chown -R 1000:1000 /tmp/web.conf


USER splunk

# add splunk to the path
RUN if [[ -e /opt/splunk-etc ]];then \
        echo -e '\nexport PATH=$PATH:/opt/splunk/bin' >> $HOME/.bashrc ; fi

RUN if [[ -e /opt/splunkforwarder-etc ]];then \
        echo -e '\nexport PATH=$PATH:/opt/splunkforwarder/bin' >> $HOME/.bashrc ; fi

# disable caching of web assets on splunk servers
RUN if [[ -e /opt/splunk-etc ]];then \
        mkdir -p /opt/splunk-etc/system/local && \
        cp /tmp/web.conf /opt/splunk-etc/system/local/web.conf ; fi
RUN rm -f /tmp/web.conf

# install suit toolkit if splunk server
RUN if [[ -e /opt/splunk-etc ]];then \
        (curl -s -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.38.0/install.sh | bash) && \
        source ~/.bashrc && \
        nvm install lts/fermium && \
        npm install -g @splunk/create && \
        npm install -g yarn ; fi

# install jdk if splunk server
USER root
COPY <<'EOF' /etc/yum.repos.d/mongodb-org-7.0.repo
[mongodb-org-7.0]
name=MongoDB Repository
baseurl=https://repo.mongodb.org/yum/redhat/$releasever/mongodb-org/7.0/$basearch/
gpgcheck=1
enabled=1
gpgkey=https://www.mongodb.org/static/pgp/server-7.0.asc
EOF

COPY <<'EOF' /tmp/mongowhat
mongosh --quiet --tlsAllowInvalidCertificates --tls localhost:8191/local --username __system --password $(cat var/lib/splunk/kvstore/mongo/splunk.key) --eval '
const all = db.adminCommand({ listDatabases: 1 }).databases.map((dbx) => {
    const ndb = db.getSiblingDB(dbx.name);
    const dbcontent = ndb.getCollectionNames().map((col) => {
        return {
            collection: col, contents: ndb.getCollection(col).find().toArray()
        };
    });
    return { db: dbx.name, content: dbcontent };
});
print(JSON.stringify(all))
'
EOF

RUN if [[ -e /opt/splunk-etc ]];then \
        mv /tmp/mongowhat /opt/splunk/bin && \
        chmod +x /opt/splunk/bin/mongowhat && \
        chown splunk:splunk /opt/splunk/bin/mongowhat && \
        microdnf install -y java-11-openjdk-headless mongodb-mongosh && \
        microdnf clean all; fi

USER ansible

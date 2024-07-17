ARG VERSION=8.2.0
ARG TOOL=splunk
FROM splunk/${TOOL}:${VERSION}


USER root

# Do this 1st - it takes the longest
RUN sed -i 's/41812/1000/g' /etc/passwd && \
    sed -i 's/41812/1000/g' /etc/group && \
    chown -R 1000:1000 /home/splunk /opt/splunk* 

RUN update-ca-trust && \
    microdnf install -y vim git-core jq nmap net-tools lsof && \
    microdnf clean all

RUN curl -s -L -f -o /tmp/tcpdump.rpm http://vault.centos.org/8-stream/AppStream/x86_64/os/Packages/tcpdump-4.9.3-1.el8.x86_64.rpm && \
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

USER ansible

ARG VERSION=8.2.0
ARG TOOL=splunk
FROM splunk/${TOOL}:${VERSION}

USER root

RUN update-ca-trust && \
    microdnf install -y vim git-core jq nmap net-tools lsof && \
    microdnf clean all

RUN sed -i 's/41812/1000/g' /etc/passwd && \
    sed -i 's/41812/1000/g' /etc/group && \
    chown -R 1000:1000 /home/splunk /opt/splunk*

ADD ./refresh /usr/bin/refresh

USER ansible

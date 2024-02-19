FROM ubuntu:22.04

RUN groupadd -g 1000 splunk
RUN useradd -u 1000 -g 1000 -m splunk
ARG ASSET=splunk-9.0.4-de405f4a7979-Linux-x86_64.tgz

COPY $ASSET /tmp/splunk.tgz
RUN tar -xf /tmp/splunk.tgz -C /opt

RUN chown -R splunk:splunk /opt/splunk && rm /tmp/splunk.tgz

RUN apt update && apt install -y curl vim jq net-tools iproute2 && rm -rf /var/lib/apt/lists/*

COPY ./entrypoint /sbin/entrypoint

USER splunk
RUN mkdir -p /opt/splunk/var/log/client_events
RUN echo "\nOPTIMISTIC_ABOUT_FILE_LOCKING=1" >> /opt/splunk/etc/splunk-launch.conf.default

ENTRYPOINT ["/sbin/entrypoint"]


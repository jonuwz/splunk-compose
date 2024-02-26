FROM ubuntu:22.04

RUN groupadd -g 1000 splunk
RUN useradd -u 1000 -g 1000 -m splunk
ARG ASSET=splunkforwarder-9.0.4-de405f4a7979-Linux-x86_64.tgz

COPY $ASSET /tmp/splunkforwarder.tgz
RUN tar -xf /tmp/splunkforwarder.tgz -C /opt

RUN chown -R splunk:splunk /opt/splunkforwarder && rm /tmp/splunkforwarder.tgz

RUN apt update && apt install -y curl python3 python3-requests vim jq net-tools iproute2 && rm -rf /var/lib/apt/lists/*

COPY ./entrypoint /sbin/entrypoint

USER splunk

ENTRYPOINT ["/sbin/entrypoint"]


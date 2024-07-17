FROM haproxy:2.3

USER root 
RUN sed -i 's/^haproxy:/haproxy:x:1000:/' /etc/group && sed -i 's@^haproxy:.*@haproxy:x:99:99::/var/lib/haproxy:/bin/sh@' /etc/passwd && chown -R 1000:1000 /var/lib/haproxy

EXPOSE 8000 8089 8088 8404
USER haproxy


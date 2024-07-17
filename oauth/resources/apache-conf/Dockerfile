FROM debian:bookworm-slim as build

WORKDIR /build

RUN apt-get update && \
  apt-get install -y ca-certificates make automake git g++ libtool pkg-config autoconf libssl-dev check libjansson-dev libz-dev procps apache2 apache2-dev curl && \
  curl -L -o /tmp/t.deb https://github.com/OpenIDC/mod_auth_openidc/releases/download/v2.4.15.7/libapache2-mod-auth-openidc_2.4.15.7-1.bookworm_amd64.deb && \
  apt-get install -y /tmp/t.deb && \
  rm -f /tmp/t.deb && \
  rm -rf /var/lib/apt/lists/*
  
ARG LIBJWT_VERSION=1.17.1
ARG MOD_AUTHNZ_JWT_VERSION=1.2.0

RUN git clone https://github.com/benmcollins/libjwt.git && \
    cd libjwt && \
    git checkout tags/v$LIBJWT_VERSION && \
    autoreconf -i && \
    ./configure && \
    make && \
    make install

RUN git clone https://github.com/AnthonyDeroche/mod_authnz_jwt.git && \
    cd mod_authnz_jwt && \
    git checkout tags/v$MOD_AUTHNZ_JWT_VERSION && \
    autoreconf -ivf && \
    PKG_CONFIG_PATH=/usr/local ./configure && \
    make && \
    make install
    
FROM httpd:2.4

COPY --from=build /usr/local/lib/libjwt.so /usr/lib/x86_64-linux-gnu/libjwt.so.1
COPY --from=build /usr/lib/apache2/modules/mod_authnz_jwt.so /usr/local/apache2/modules/mod_authnz_jwt.so

RUN echo "LoadModule auth_jwt_module modules/mod_authnz_jwt.so" >> /usr/local/apache2/conf/httpd.conf
RUN echo "LoadModule auth_jwt_module modules/mod_authnz_jwt.so" >> /usr/local/apache2/conf/httpd.conf

RUN apt-get update && \
  apt-get install -y curl && \ 
  curl -L -o /tmp/t.deb https://github.com/OpenIDC/mod_auth_openidc/releases/download/v2.4.15.7/libapache2-mod-auth-openidc_2.4.15.7-1.bookworm_amd64.deb && \
  apt-get install -y /tmp/t.deb && \
  rm -f /tmp/t.deb && \
  rm -rf /var/lib/apt/lists/*

RUN cp /usr/lib/apache2/modules/mod_auth_openidc.so /usr/local/apache2/modules

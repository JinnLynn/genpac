FROM jinnlynn/python:3.10

LABEL maintainer="JinnLynn <eatfishlin@gmail.com>"

RUN set -ex && \
    apk add --no-cache uwsgi-python3

COPY genpac/ /tmp/genpac/
COPY setup.py /tmp
COPY example/server/config.ini /app/etc/
COPY example/server/docker-entrypoint.sh /app/bin/entrypoint

RUN set -ex && \
    pip install --no-cache-dir /tmp[server] && \
    rm -rf /tmp/*

ENV GENPAC_CONFIG=/app/etc/config.ini

ENTRYPOINT [ "entrypoint" ]

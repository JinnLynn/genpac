FROM jinnlynn/python:3.12

LABEL maintainer="JinnLynn <eatfishlin@gmail.com>"

COPY src/genpac/ /tmp/genpac/src/genpac/
COPY pyproject.toml README.md /tmp/genpac/
COPY example/server/config.ini /app/etc/
COPY example/server/docker-entrypoint.sh /app/bin/entrypoint

RUN set -ex && \
    apk add --no-cache --virtual .build build-base linux-headers && \
    pip install --no-cache-dir uwsgi /tmp/genpac[server] && \
    apk del .build && \
    rm -rf /tmp/*

ENV GENPAC_CONFIG=/app/etc/config.ini

ENTRYPOINT [ "entrypoint" ]

FROM python:3
LABEL maintainer="chochlik@gmail.com"

ENV CTCACHE_PORT=5000

RUN mkdir -p /var/lib/ctcache
WORKDIR /usr/src/app

COPY src/ctcache/clang-tidy-cache-server requirements.txt ./
COPY static/ ./static/
RUN pip install --no-cache-dir -r requirements.txt

CMD  "python" "./clang-tidy-cache-server" \
    "--save-path"  "/var/lib/ctcache/data.json.gz" \
    "--port" "${CTCACHE_PORT}"

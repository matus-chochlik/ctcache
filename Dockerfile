FROM python:3
LABEL maintainer="chochlik@gmail.com"

ENV CTCACHE_PORT=5000

RUN mkdir -p /var/run/ctcache
WORKDIR /usr/src/app

COPY clang-tidy-cache-server requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

CMD  "python" "./clang-tidy-cache-server" \
    "--save-path"  "/var/run/ctcache" \
    "--stats-path" "/var/run/ctcache" \
    "--port" "${CTCACHE_PORT}"

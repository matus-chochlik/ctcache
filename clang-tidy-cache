#!/usr/bin/env python3
# coding: UTF-8
# Copyright (c) 2019-2022 Matus Chochlik
# Distributed under the Boost Software License, Version 1.0.
# See accompanying file LICENSE_1_0.txt or copy at
#  http://www.boost.org/LICENSE_1_0.txt

import os
import re
import sys
import errno
import getpass
import logging
import hashlib
import tempfile
import subprocess
import json
import shlex
import typing as tp

try:
    import redis
except ImportError:
    redis = None

# ------------------------------------------------------------------------------
class ClangTidyCacheOpts(object):
    # --------------------------------------------------------------------------
    def __init__(self, log, args):
        self._original_args = args
        self._clang_tidy_args = []
        self._compiler_args = []
        self._cache_dir = ""
        self._compile_commands_db = None

        self._strip_list = os.getenv("CTCACHE_STRIP", "").split(':')

        # splits arguments starting with - on the first =
        args = [arg.split('=', 1) if arg.startswith('-p') else [arg] for arg in args]
        args = [arg for sub in args for arg in sub]

        if args.count("--") == 1:
            # Invoked with compiler args on the actual command line
            i = args.index("--")
            self._clang_tidy_args = args[:i]
            self._compiler_args = args[i+1:]
        elif args.count("-p") == 1:
            # Invoked with compiler args in a compile commands json db
            i = args.index("-p")
            self._clang_tidy_args = args

            i += 1
            if i >= len(args):
                return

            cdb_path = args[i]
            cdb = os.path.join(cdb_path, "compile_commands.json")
            self._load_compile_command_db(cdb)

            i += 1
            if i >= len(args):
                return

            # This assumes that the filename occurs after the -p <cdb path>
            # and that there is only one of them
            filenames = [arg for arg in args[i:] if not arg.startswith("-")]
            if len(filenames) > 0:
                self._compiler_args = self._compiler_args_for(filenames[0])

        if self._compiler_args:
            self._compiler_args.insert(1, "-D__clang_analyzer__=1")
            for i in range(1, len(self._compiler_args)):
                if self._compiler_args[i-1] in ["-o", "--output"]:
                    self._compiler_args[i] = "-"
                if self._compiler_args[i-1] in ["-c"]:
                    self._compiler_args[i-1] = "-E"

    # --------------------------------------------------------------------------
    def _load_compile_command_db(self, filename):
        try:
            f = open(filename)
            self._compile_commands_db = json.load(f)
            f.close()
        except Exception:
            return False

    # --------------------------------------------------------------------------
    def _compiler_args_for(self, filename):
        if self._compile_commands_db == None:
            return []

        filename = os.path.expanduser(filename)
        filename = os.path.realpath(filename)

        for command in self._compile_commands_db:
            db_filename = command["file"]
            if os.path.samefile(filename, db_filename):
                try:
                    return shlex.split(command["command"])
                except KeyError:
                    try:
                        return shlex.split(command["arguments"][0])
                    except:
                        return "clang-tidy"

        return []

    # --------------------------------------------------------------------------
    def should_print_dir(self):
        try:
            return self._original_args[0] == "--cache-dir"
        except IndexError:
            return False

    # --------------------------------------------------------------------------
    def should_print_stats(self):
        try:
            return self._original_args[0] == "--show-stats"
        except IndexError:
            return False

    # --------------------------------------------------------------------------
    def should_remove_dir(self):
        try:
            return self._original_args[0] == "--clean"
        except IndexError:
            return False

    # --------------------------------------------------------------------------
    def original_args(self):
        return self._original_args

    # --------------------------------------------------------------------------
    def clang_tidy_args(self):
        return self._clang_tidy_args

    # --------------------------------------------------------------------------
    def compiler_args(self):
        return self._compiler_args

    # --------------------------------------------------------------------------
    @property
    def cache_dir(self):
        if self._cache_dir:
            return self._cache_dir

        try:
            user = getpass.getuser()
        except KeyError:
            user = "unknown"
        self._cache_dir = os.getenv(
            "CTCACHE_DIR",
            os.path.join(
                tempfile.tempdir if tempfile.tempdir else "/tmp", "ctcache-" + user
            ),
        )
        return self._cache_dir

    # --------------------------------------------------------------------------
    def adjust_chunk(self, x):
        x = x.strip()
        r = str().encode("utf8")
        if not x.startswith("# "):
            for w in x.split():
                w = w.strip('"')
                if os.path.exists(w):
                    w = os.path.realpath(w)
                for item in self._strip_list:
                    w = w.replace(item, '')
                w.strip()
                if w:
                    r += w.encode("utf8")
        return r

    # --------------------------------------------------------------------------
    def has_s3(self):
        return "CTCACHE_S3_BUCKET" in os.environ

    # --------------------------------------------------------------------------
    def s3_bucket(self):
        return os.getenv("CTCACHE_S3_BUCKET")

    # --------------------------------------------------------------------------
    def s3_bucket_folder(self):
        return os.getenv("CTCACHE_S3_FOLDER", 'clang-tidy-cache')

    # --------------------------------------------------------------------------
    def s3_no_credentials(self):
        return os.getenv("CTCACHE_S3_NO_CREDENTIALS", "")

    # --------------------------------------------------------------------------
    def has_host(self):
        return os.getenv("CTCACHE_HOST") is not None

    # --------------------------------------------------------------------------
    def rest_host(self):
        return os.getenv("CTCACHE_HOST", "localhost")

    # --------------------------------------------------------------------------
    def rest_proto(self):
        return os.getenv("CTCACHE_PROTO", "http")

    # --------------------------------------------------------------------------
    def rest_port(self):
        return int(os.getenv("CTCACHE_PORT", 5000))

    # --------------------------------------------------------------------------
    def save_output(self) -> bool:
        return os.getenv("CTCACHE_SAVE_OUTPUT", "1") == "1"

    # --------------------------------------------------------------------------
    def ignore_output(self) -> bool:
        return self.save_output() or "CTCACHE_IGNORE_OUTPUT" in os.environ

    # --------------------------------------------------------------------------
    def debug_enabled(self):
        return "CTCACHE_DEBUG" in os.environ

    # --------------------------------------------------------------------------
    def dump_enabled(self):
        return "CTCACHE_DUMP" in os.environ

    # --------------------------------------------------------------------------
    def has_redis_host(self) -> bool:
        return "CTCACHE_REDIS_HOST" in os.environ

    # --------------------------------------------------------------------------
    def redis_host(self) -> str:
        return os.getenv("CTCACHE_REDIS_HOST", "")

    # --------------------------------------------------------------------------
    def redis_port(self) -> int:
        return int(os.getenv("CTCACHE_REDIS_PORT", "6379"))

    # --------------------------------------------------------------------------
    def redis_username(self) -> str:
        return os.getenv("CTCACHE_REDIS_USERNAME", "")

    # --------------------------------------------------------------------------
    def redis_password(self) -> str:
        return os.getenv("CTCACHE_REDIS_PASSWORD", "")

    # --------------------------------------------------------------------------
    def redis_namespace(self) -> str:
        return os.getenv("CTCACHE_REDIS_NAMESPACE", "ctcache/")


# ------------------------------------------------------------------------------
class ClangTidyCacheHash(object):
    # --------------------------------------------------------------------------
    def _opendump(self, opts):
        return open(os.path.join(tempfile.gettempdir(), "ctcache.dump"), "ab")

    # --------------------------------------------------------------------------
    def __init__(self, opts):
        self._hash = hashlib.sha1()
        self._dump = self._opendump(opts) if opts.dump_enabled() else None
        assert self._dump or not opts.dump_enabled()

    # --------------------------------------------------------------------------
    def __del__(self):
        if self._dump:
            self._dump.close()

    # --------------------------------------------------------------------------
    def update(self, content):
        if content:
            self._hash.update(content)
            if self._dump:
                self._dump.write(content)

    # --------------------------------------------------------------------------
    def hexdigest(self):
        return self._hash.hexdigest()

# ------------------------------------------------------------------------------
class ClangTidyServerCache(object):
    def __init__(self, log, opts):
        import requests
        self._requests = requests
        self._log = log
        self._opts = opts

    # --------------------------------------------------------------------------
    def is_cached(self, digest):
        try:
            query = self._requests.get(self._make_query_url(digest), timeout=3)
            if query.status_code == 200:
                if query.json() == True:
                    return True
                elif query.json() == False:
                    return False
                else:
                    self._log.error("is_cached: Can't connect to server {0}, error {1}".format(
                        self._opts.rest_host(), query.status_code))
        except:
            pass
        return False

    # --------------------------------------------------------------------------
    def store_in_cache(self, digest):
        try:
            query = self._requests.get(self._make_store_url(digest), timeout=3)
            if query.status_code == 200:
                return
            else:
                self._log.error("store_in_cache: Can't store data in server {0}, error {1}".format(
                    self._opts.rest_host(), query.status_code))
        except:
            pass

    # --------------------------------------------------------------------------
    def query_stats(self, options):
        try:
            query = self._requests.get(self._make_stats_url(), timeout=3)
            if query.status_code == 200:
                return query.json()
            else:
                self._log.error("query_stats: Can't connect to server {0}, error {1}".format(
                    self._opts.rest_host(), query.status_code))
        except:
            pass
        return {}

    # --------------------------------------------------------------------------
    def _make_query_url(self, digest):
        return "%(proto)s://%(host)s:%(port)d/is_cached/%(digest)s" % {
            "proto": self._opts.rest_proto(),
            "host": self._opts.rest_host(),
            "port": self._opts.rest_port(),
            "digest": digest
        }

    # --------------------------------------------------------------------------
    def _make_store_url(self, digest):
        return "%(proto)s://%(host)s:%(port)d/cache/%(digest)s" % {
            "proto": self._opts.rest_proto(),
            "host": self._opts.rest_host(),
            "port": self._opts.rest_port(),
            "digest": digest
        }

    # --------------------------------------------------------------------------
    def _make_stats_url(self):
        return "%(proto)s://%(host)s:%(port)d/stats" % {
            "proto": self._opts.rest_proto(),
            "host": self._opts.rest_host(),
            "port": self._opts.rest_port()
        }

# ------------------------------------------------------------------------------
class ClangTidyLocalCache(object):
    # --------------------------------------------------------------------------
    def __init__(self, log, opts):
        self._log = log
        self._opts = opts

    # --------------------------------------------------------------------------
    def is_cached(self, digest):
        path = self._make_path(digest)
        if os.path.isfile(path):
            os.utime(path, None)
            return True

        return False

    # --------------------------------------------------------------------------
    def get_cache_data(self, digest) -> tp.Optional[bytes]:
        path = self._make_path(digest)
        if os.path.isfile(path):
            os.utime(path, None)
            with open(path, "rb") as stream:
                return stream.read()
        else:
            return None

    # --------------------------------------------------------------------------
    def store_in_cache(self, digest):
        p = self._make_path(digest)
        self._mkdir_p(os.path.dirname(p))
        open(p, "w").close()

    # --------------------------------------------------------------------------
    def store_in_cache_with_data(self, digest, data: bytes):
        p = self._make_path(digest)
        self._mkdir_p(os.path.dirname(p))
        with open(p, "wb") as stream:
            stream.write(data)

    # --------------------------------------------------------------------------
    def _mkdir_p(self, path):
        try:
            os.makedirs(path)
        except OSError as os_error:
            if os_error.errno == errno.EEXIST and os.path.isdir(path):
                pass
            else:
                raise

    # --------------------------------------------------------------------------
    def _make_path(self, digest):
        return os.path.join(self._opts.cache_dir, digest[:2], digest[2:])


class ClangTidyRedisCache(object):
    def __init__(self, log, opts: ClangTidyCacheOpts):
        self._log = log
        self._opts = opts
        assert redis
        self._cli = redis.Redis(
            host=opts.redis_host(),
            port=opts.redis_port(),
            username=opts.redis_username(),
            password=opts.redis_password(),
        )
        self._namespace = opts.redis_namespace()

    def _get_key_from_digest(self, digest) -> str:
        return self._namespace + digest

    def is_cached(self, digest) -> bool:
        n_digest = self._get_key_from_digest(digest)
        return self._cli.get(n_digest) is not None

    def get_cache_data(self, digest) -> tp.Optional[bytes]:
        n_digest = self._get_key_from_digest(digest)
        return self._cli.get(n_digest)

    def store_in_cache(self, digest):
        n_digest = self._get_key_from_digest(digest)
        self._cli.set(n_digest, "")

    def store_in_cache_with_data(self, digest, data: bytes):
        n_digest = self._get_key_from_digest(digest)
        self._cli.set(n_digest, data)

# ------------------------------------------------------------------------------
class ClangTidyS3Cache(object):
    # --------------------------------------------------------------------------
    def __init__(self, log, opts):
        from boto3 import client
        from botocore.exceptions import ClientError
        from botocore.config import Config
        from botocore.session import UNSIGNED

        self._ClientError = ClientError
        self._log = log
        self._opts = opts
        if self._opts.s3_no_credentials():
            self._client = client("s3", config=Config(signature_version=UNSIGNED))
        else:
            self._client = client("s3")
        self._bucket = opts.s3_bucket()
        self._bucket_folder = opts.s3_bucket_folder()

    # --------------------------------------------------------------------------
    def is_cached(self, digest):
        try:
            path = self._make_path(digest)
            self._client.get_object(Bucket=self._bucket, Key=path)
        except self._ClientError as e:
            if e.response['Error']['Code'] == "NoSuchKey":
                return False
            else:
                self._log.error(
                    "Error calling S3:get_object {}".format(str(e)))
                raise

        return True

    # --------------------------------------------------------------------------
    def store_in_cache(self, digest):
        if self._opts.s3_no_credentials():
            return
        try:
            path = self._make_path(digest)
            self._client.put_object(Bucket=self._bucket, Key=path, Body=digest)
        except self._ClientError as e:
            self._log.error("Error calling S3:put_object {}".format(str(e)))
            raise

    # --------------------------------------------------------------------------
    def _make_path(self, digest):
        return os.path.join(
            self._bucket_folder,
            digest[:2],
            digest[2:]
        )

# ------------------------------------------------------------------------------
class ClangTidyCache(object):
    # --------------------------------------------------------------------------
    def __init__(self, log, opts: ClangTidyCacheOpts):
        self._log = log
        self._opts = opts
        self._local_cache = ClangTidyLocalCache(log, opts)
        self._redis_cache = ClangTidyRedisCache(
            log, opts) if opts.has_redis_host() and redis else None
        self._server_cache = ClangTidyServerCache(
            log, opts) if opts.has_host() else None
        self._s3_cache = ClangTidyS3Cache(
            log, opts) if opts.has_s3() else None

    # --------------------------------------------------------------------------
    def is_cached(self, digest):
        if self._local_cache.is_cached(digest):
            return True

        if self._server_cache != None and self._server_cache.is_cached(digest):
            return True

        if self._s3_cache != None and self._s3_cache.is_cached(digest):
            return True

        if self._redis_cache is not None and self._redis_cache.is_cached(digest):
            return True

        return False

    # --------------------------------------------------------------------------
    def get_cache_data(self, digest) -> tp.Optional[bytes]:
        data = self._local_cache.get_cache_data(digest)
        if data is None and self._redis_cache is not None:
            data = self._redis_cache.get_cache_data(digest)

        # TODO: add support for stdout storage for server cache and s3 cache
        return data

    # --------------------------------------------------------------------------
    def store_in_cache(self, digest):
        self._local_cache.store_in_cache(digest)

        if self._server_cache != None:
            self._server_cache.store_in_cache(digest)

        if self._s3_cache != None:
            self._s3_cache.store_in_cache(digest)

        if self._redis_cache is not None:
            self._redis_cache.store_in_cache(digest)

    # --------------------------------------------------------------------------
    def store_in_cache_with_data(self, digest, data: bytes):
        self._local_cache.store_in_cache_with_data(digest, data)

        if self._redis_cache is not None:
            self._redis_cache.store_in_cache_with_data(digest, data)

        # TODO: add support for stdout storage for server cache and s3 cache

    # --------------------------------------------------------------------------
    def query_stats(self, options):
        if self._server_cache is not None:
            return self._server_cache.query_stats(options)

        return {}


# ------------------------------------------------------------------------------
source_file_change_re = re.compile(r'#\s+\d+\s+"([^"]+)".*')

def source_file_changed(cpp_line):
    found = source_file_change_re.match(cpp_line)
    if found:
        found_path = found.group(1)
        if os.path.isfile(found_path):
            return os.path.realpath(os.path.dirname(found_path))

# ------------------------------------------------------------------------------
def find_ct_config(search_path):
    while search_path and search_path != "/":
        search_path = os.path.dirname(search_path)
        ct_config = os.path.join(search_path, '.clang-tidy')
        if os.path.isfile(ct_config):
            return ct_config

# ------------------------------------------------------------------------------
def hash_inputs(opts):
    co_args = opts.compiler_args()
    ct_args = opts.clang_tidy_args()
    if not co_args and not ct_args:
        return None

    if len(co_args) == 0:
        return None

    result = ClangTidyCacheHash(opts)

    proc = subprocess.Popen(
        co_args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout, stderr = proc.communicate()
    if stderr:
        return None

    src_to_ct_config = dict()
    ct_config_paths = set()

    for line in stdout.splitlines():
        line = line.decode("utf8")
        search_path = source_file_changed(line)
        if search_path:
            try:
                ct_config_path = src_to_ct_config[search_path]
            except KeyError:
                ct_config_path = find_ct_config(search_path)
                src_to_ct_config[search_path] = ct_config_path

            if ct_config_path:
                ct_config_paths.add(ct_config_path)

        chunk = opts.adjust_chunk(line)
        result.update(chunk)

    for ct_config_path in sorted(ct_config_paths):
        with open(ct_config_path, "rt") as ct_config:
            for line in ct_config.readlines():
                chunk = opts.adjust_chunk(line)
                result.update(chunk)

    def _omit_after(args, excl):
        omit_next = False
        for arg in args:
            omit_this = arg in excl
            if not omit_this and not omit_next:
                yield arg
            omit_next = omit_this

    ct_args = list(_omit_after(ct_args, ["-export-fixes"]))

    for chunk in sorted(set([opts.adjust_chunk(arg) for arg in co_args[1:]])):
        result.update(chunk)
    for chunk in sorted(set([opts.adjust_chunk(arg) for arg in ct_args[1:]])):
        result.update(chunk)

    return result.hexdigest()

# ------------------------------------------------------------------------------
def print_stats(log, opts):
    def _format_bytes(s):
        if s < 10000:
            return "%d B" % (s)
        if s < 10000000:
            return "%d kB" % (s / 1000)
        return "%d MB" % (s / 1000000)

    def _format_time(s):
        if s < 60:
            return "%d seconds" % (s)
        if s < 3600:
            return "%d minutes %d seconds" % (s / 60, s % 60)
        if s < 86400:
            return "%d hours %d minutes" % (s / 3600, (s / 60) % 60)
        if s < 604800:
            return "%d days %d hours" % (s / 86400, (s / 3600) % 24)
        if int(s / 86400) % 7 == 0:
            return "%d weeks" % (s / 604800)
        return "%d weeks %d days" % (s / 604800, (s / 86400) % 7)

    cache = ClangTidyCache(log, opts)
    stats = cache.query_stats(opts)
    entries = [
        ("Server host", lambda o, s: o.rest_host()),
        ("Server port", lambda o, s: "%d" % o.rest_port()),
        ("Long-term hit rate", lambda o, s: "%.1f %%" %
         (s["total_hit_rate"] * 100.0)),
        ("Hit rate", lambda o, s: "%.1f %%" % (s["hit_rate"] * 100.0)),
        ("Hit count", lambda o, s: "%d" % s["hit_count"]),
        ("Miss count", lambda o, s: "%d" % s["miss_count"]),
        ("Miss rate", lambda o, s: "%.1f %%" % (s["miss_rate"] * 100.0)),
        ("Max hash age", lambda o, s: "%d days" %
         max(int(k) for k in s["age_days_histogram"])),
        ("Max hash hits", lambda o, s: "%d" % max(int(k)
         for k in s["hit_count_histogram"])),
        ("Cache size", lambda o, s: _format_bytes(s["saved_size_bytes"])),
        ("Cached hashes", lambda o, s: "%d" % s["cached_count"]),
        ("Cleaned hashes", lambda o, s: "%d" % s["cleaned_count"]),
        ("Cleaned ago", lambda o, s: _format_time(s["cleaned_seconds_ago"])),
        ("Saved ago", lambda o, s: _format_time(s["saved_seconds_ago"])),
        ("Uptime", lambda o, s: _format_time(s["uptime_seconds"]))
    ]

    max_len = max(len(e[0]) for e in entries)
    for label, fmtfunc in entries:
        padding = " " * (max_len-len(label))
        try:
            print(label+":", padding, fmtfunc(opts, stats))
        except:
            print(label+":", padding, "N/A")

# ------------------------------------------------------------------------------
def run_clang_tidy_cached(log, opts):
    cache = ClangTidyCache(log, opts)
    digest = None
    try:
        digest = hash_inputs(opts)
        if digest and opts.save_output():
            data = cache.get_cache_data(digest)
            if data is not None:
                sys.stdout.write(data.decode("utf8"))
                return 0
        elif digest and cache.is_cached(digest):
            return 0
        else:
            pass
    except Exception as error:
        log.error(str(error))

    proc = subprocess.Popen(
        opts.original_args(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout, stderr = proc.communicate()
    sys.stdout.write(stdout.decode("utf8"))
    sys.stderr.write(stderr.decode("utf8"))

    tidy_success = True
    if proc.returncode != 0:
        tidy_success = False

    if stdout and not opts.ignore_output():
        tidy_success = False

    if tidy_success and digest:
        try:
            if opts.save_output():
                cache.store_in_cache_with_data(digest, stdout)
            else:
                cache.store_in_cache(digest)
        except Exception as error:
            log.error(str(error))

    return proc.returncode

# ------------------------------------------------------------------------------
def main():
    log = logging.getLogger(os.path.basename(__file__))
    log.setLevel(logging.WARNING)
    debug = False
    try:
        opts = ClangTidyCacheOpts(log, sys.argv[1:])
        debug = opts.debug_enabled()
        if opts.should_print_dir():
            print(opts.cache_dir)
        elif opts.should_remove_dir():
            import shutil
            try:
                shutil.rmtree(opts.cache_dir)
            except FileNotFoundError:
                pass
        elif opts.should_print_stats():
            print_stats(log, opts)
        else:
            return run_clang_tidy_cached(log, opts)
        return 0
    except Exception as error:
        if debug:
            raise
        else:
            log.error("%s: %s" % (str(type(error)), str(error)))
        return 1


# ------------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(main())

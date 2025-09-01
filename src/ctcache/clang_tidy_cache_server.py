#!/usr/bin/env python3
# coding: UTF-8
# Copyright (c) 2020-2024 Matus Chochlik
# Distributed under the Boost Software License, Version 1.0.
# See accompanying file LICENSE_1_0.txt or copy at
#  http://www.boost.org/LICENSE_1_0.txt

import os
import sys
import re
import io
import math
import json
import time
import gzip
import flask
import shutil
import argparse
import matplotlib.pyplot as plt
import matplotlib.ticker as pltckr

# ------------------------------------------------------------------------------
class ArgumentParser(argparse.ArgumentParser):
    # -------------------------------------------------------------------------
    def __init__(self, **kw):
        argparse.ArgumentParser.__init__(self, **kw)

        def save_interval(x):
            try:
                p = float(x)
                if (p >= 10.0):
                    return p
                self.error("'%f' is not a valid save interval" % (p))
            except TypeError:
                self.error("save interval must be a numeric value not less than 10")

        def cleanup_interval(x):
            try:
                p = float(x)
                if (p >= 1.0):
                    return p
                self.error("'%f' is not a valid cleanup interval" % (p))
            except TypeError:
                self.error("cleanup interval must be a numeric value not less than 1")

        def max_cache_size(x):
            try:
                p = int(float(x) * 2 ** 30)
                if (p > 0):
                    return p
                self.error("'%f' is not a valid max cache size" % (p))
            except TypeError:
                self.error("max cache size must be a numeric value greater than 0")

        def port_number(x):
            try:
                p = int(x)
                if (p > 1) and (p < 2**16):
                    return p
                self.error("'%d' is not a valid port number" % (p))
            except TypeError:
                self.error("port number must be an integer value")

        self.add_argument(
            "--port", "-P",
            dest="port_number",
            metavar="NUMBER",
            type=port_number,
            default=5000,
            help="""
            Specifies the port number (5000) by default.
            """)

        self.add_argument(
            "--save-path", "-S",
            dest="save_path",
            metavar="FILE-PATH.gz",
            type=os.path.realpath,
            default=os.path.join(os.path.expanduser("~"), ".cache", "ctcache.json.gz"),
            help="""
            Specifies the path to the persistent save file.
            """)

        self.add_argument(
            "--save-interval", "-I",
            dest="save_interval",
            metavar="NUMBER",
            type=save_interval,
            default=600,
            help="""
            Specifies the cache-data save time interval in seconds.
            """)

        self.add_argument(
            "--stats-save-interval", "-Z",
            dest="stats_save_interval",
            metavar="NUMBER",
            type=save_interval,
            default=3600,
            help="""
            Specifies the statistics save time interval in seconds.
            """)

        self.add_argument(
            "--cleanup-interval", "-C",
            dest="cleanup_interval",
            metavar="NUMBER",
            type=cleanup_interval,
            default=60,
            help="""
            Specifies the cleanup time interval in seconds.
            """)

        self.add_argument(
            "--stats-path", "-U",
            dest="stats_path",
            metavar="DIR-PATH",
            type=os.path.realpath,
            default=None,
            help="""
            Specifies the path to a directory where statistics should be stored.
            """)

        self.add_argument(
            "--chart-path", "-G",
            dest="chart_path",
            metavar="DIR-PATH",
            type=os.path.realpath,
            default=None,
            help="""
            Specifies the path to a directory where charts should be stored.
            """)

        self.add_argument(
            "--max-cache-size", "-M",
            dest="max_cache_size",
            metavar="NUMBER",
            type=max_cache_size,
            default=5,
            help="""
            Specifies the max size of cached file in gigabytes.
            """)

        self.add_argument(
            "--debug", "-D",
            dest="debug_mode",
            action="store_true",
            default=False,
            help="""
            Starts the service in debug mode.
            """)

        self.add_argument(
            "--auth-key-writes",
            dest="auth_key_writes",
            metavar="STRING",
            type=str,
            default=None,
            help="""
            If specified, all non-GET requests must supply matching ?key=STRING or are rejected (403).
            """)

    # -------------------------------------------------------------------------
    def process_parsed_options(self, options):
        return options

    # -------------------------------------------------------------------------
    def parse_args(self):
        return self.process_parsed_options(
            argparse.ArgumentParser.parse_args(self))

# ------------------------------------------------------------------------------
def get_argument_parser():
    return ArgumentParser(
        prog=os.path.basename(__file__),
        description="""server maintaining cached values for clang-tidy-cache""")
# ------------------------------------------------------------------------------
class CacheFile():
    # -------------------------------------------------------------------------
    @staticmethod
    def get_cache_file_path(hashstr):
        return os.path.join(ctcache_app.config["CACHE_FOLDER"], hashstr)

    # -------------------------------------------------------------------------
    def __init__(self, hashstr):
        self._filepath = self.get_cache_file_path(hashstr)
        self._hashstr = hashstr
        self._data = bytes()

    # -------------------------------------------------------------------------
    def save(self, data):
        f = open(self._filepath, 'w')
        f.write(data)
        f.close()

    # -------------------------------------------------------------------------
    def remove(self):
        try:
            os.remove(self._filepath)
        except FileNotFoundError:
            # file already removed
            pass

    # -------------------------------------------------------------------------
    def size(self):
        try:
            return os.path.getsize(self._filepath)
        except FileNotFoundError:
            # file already removed
            return 0

    # -------------------------------------------------------------------------
    def mtime(self):
        try:
            return os.path.getmtime(self._filepath)
        except FileNotFoundError:
            # file already removed
            return 0


# ------------------------------------------------------------------------------
class ClangTidyCacheApp(flask.Flask):
    # --------------------------------------------------------------------------
    @staticmethod
    def get_static_folder():
        return os.path.join(
            os.path.realpath(
                os.environ.get('CTCACHE_WEBROOT', os.path.dirname(__file__))
            ),
            'static')
    # --------------------------------------------------------------------------
    @staticmethod
    def get_cache_folder():
        return os.path.join(
            os.path.realpath(
                os.environ.get('CTCACHE_WEBROOT', os.path.dirname(__file__))
            ),
            'cache')
    # --------------------------------------------------------------------------
    def __init__(self):
        flask.Flask.__init__(self, "clang-tidy-cache")

        self.config["STATIC_FOLDER"] = self.get_static_folder()
        os.makedirs(self.config["STATIC_FOLDER"], exist_ok=True)

        self.config["CACHE_FOLDER"] = self.get_cache_folder()
        os.makedirs(self.config["CACHE_FOLDER"], exist_ok=True)

# ------------------------------------------------------------------------------
clang_tidy_cache = None
ctcache_app = ClangTidyCacheApp()

@ctcache_app.before_request
def _ctc_auth_writes():
    if flask.request.method != 'GET':
        if clang_tidy_cache.auth_key_writes and flask.request.args.get("key") != clang_tidy_cache.auth_key_writes:
            flask.abort(403)

# ------------------------------------------------------------------------------
class ClangTidyCache(object):
    # --------------------------------------------------------------------------
    def __init__(self, options):
        self._start_time = time.time()
        self._cleaned_count = 0
        self._hits_count = 0
        self._miss_count = 0
        self._cached = dict()
        self._stats = list()
        self._save_path = options.save_path
        self._save_interval = options.save_interval
        self._cleanup_interval = options.cleanup_interval
        self._stats_save_interval = options.stats_save_interval
        self._stats_path = options.stats_path
        self._chart_path = options.chart_path
        self._max_cache_size = options.max_cache_size
        self._auth_key_writes = options.auth_key_writes
        #
        self._info_getters = {
            "static_path": self.static_path,
            "save_path": self.save_path
        }
        self._stat_getters = {
            "uptime_seconds": self.uptime_seconds,
            "saved_size_bytes": self.save_file_size,
            "saved_cache_size": self.save_cache_size,
            "saved_seconds_ago": self.saved_seconds_ago,
            "cleaned_seconds_ago": self.cleaned_seconds_ago,
            "total_hit_rate": self.total_hit_rate,
            "hit_count": self.hit_count,
            "hit_rate": self.hit_rate,
            "miss_count": self.miss_count,
            "miss_rate": self.miss_rate,
            "cached_count": self.cached_count,
            "cleaned_count": self.cleaned_count,
            "age_days_histogram": self.age_days_histogram,
            "hit_count_histogram": self.hit_count_histogram
        }
        #
        self._stats_save_time = time.time()
        self._save_time = time.time()
        self._cleanup_time = time.time()
        #
        self._hash_re = re.compile(r'^[0-9a-fA-F]{40}$')
        #
        self.do_load()

    # --------------------------------------------------------------------------
    def maintain(self):
        if self.saved_stats_seconds_ago() > self._stats_save_interval:
            self.do_save_stats()
            self._stats_save_time = time.time()
        if self.saved_seconds_ago() > self._save_interval:
            self.do_save()
            self._save_time = time.time()
        if self.cleaned_seconds_ago() > self._cleanup_interval:
            self.do_cleanup()
            self.do_save_charts()
            self._cleanup_time = time.time()

    # --------------------------------------------------------------------------
    def keep_cached(self, hashstr, info):
        hit_count = info["hits"]
        kept_days = (time.time() - info["insert_time"]) / (24*3600)
        unused_days = (time.time() - info["access_time"]) / (24*3600)
        #
        if (kept_days > 30) or (kept_days > hit_count*5):
            return False
        if (unused_days > 7) or (unused_days > hit_count*3):
            return False
        return True

    # --------------------------------------------------------------------------
    def do_purge(self):
        for hashstr in self._cached:
            CacheFile(hashstr).remove()

        self._cached = dict()
        self.do_save()
        return "success"

    # --------------------------------------------------------------------------
    def _get_cache_hashstrs(self):
        d = ctcache_app.config["CACHE_FOLDER"]
        files = os.listdir(d)
        return [f for f in files if os.path.isfile(os.path.join(d, f))]

    # --------------------------------------------------------------------------
    def _remove_cache_file(self, hashstr):
        CacheFile(hashstr).remove()
        if hashstr in self._cached:
            del self._cached[hashstr]

    # --------------------------------------------------------------------------
    def _do_cleanup_by_metric(self):
        to_remove = [hashstr for hashstr, info in self._cached.items()
                     if not self.keep_cached(hashstr, info)]
        for hashstr in to_remove:
            self._remove_cache_file(hashstr)

    # --------------------------------------------------------------------------
    def _do_cleanup_invalid(self):
        for hashstr in self._get_cache_hashstrs():
            if hashstr not in self._cached:
                CacheFile(hashstr).remove()

    # --------------------------------------------------------------------------
    def _do_cleanup_least_recently_used(self):
        saved_cache_size = self.save_cache_size()
        if saved_cache_size <= self._max_cache_size:
            return

        cached_items = sorted(self._cached.items(), key = lambda v: v[1]['access_time'])
        for hashstr, _ in cached_items:
            if saved_cache_size <= self._max_cache_size:
                return

            saved_cache_size -= CacheFile(hashstr).size()
            self._remove_cache_file(hashstr)

    # --------------------------------------------------------------------------
    def do_cleanup(self):
        stats = self.get_stats()
        stats["timestamp"] = time.time()
        self._stats.append(stats)
        before = len(self._cached)

        self._do_cleanup_by_metric()
        self._do_cleanup_invalid()
        self._do_cleanup_least_recently_used()

        after = len(self._cached)
        self._cleaned_count += (before - after)

    # --------------------------------------------------------------------------
    def do_load(self):
        try:
            with gzip.open(self._save_path, 'rt', encoding="utf8") as dbf:
                for hashstr, data in json.load(dbf).items():
                    if self.is_valid_hash(hashstr):
                        try:
                            info = self._cached[hashstr] = dict()
                            info["hits"] = data["hits"]
                            info["insert_time"] = data["insert_time"]
                            info["access_time"] = data["access_time"]
                        except KeyError:
                            pass
        except Exception as err:
            print(f"Failed to load cache data: {err}", file=sys.stderr)

    # --------------------------------------------------------------------------
    def do_save(self):
        try:
            with gzip.open(self._save_path, 'wt', encoding="utf8") as dbf:
                json.dump(self._cached, dbf)
        except Exception:
            pass

    # --------------------------------------------------------------------------
    def do_save_stats(self):
        if self._stats_path is not None and os.path.isdir(self._stats_path):
            if len(self._stats) > 0:
                try:
                    path = os.path.join(
                        self._stats_path,
                        "ctcache-stats-%012d.json.tar.gz" % time.time()
                    )
                    with gzip.open(path, 'wt', encoding="utf8") as statf:
                        json.dump(self._stats, statf)
                    self._stats = list()
                except Exception as err:
                    pass
        else:
            self._stats = list()

    # --------------------------------------------------------------------------
    def do_save_charts(self):
        if self._chart_path is not None and os.path.isdir(self._chart_path):
            try:
                with self.hits_histogram_img("png") as imgb:
                    path = os.path.join(
                        self._chart_path,
                        "ctcache-hits-%012d.png" % time.time()
                    )
                    with open(path, 'wb') as imgf:
                        shutil.copyfileobj(imgb, imgf)
            except Exception as err:
                pass

    # --------------------------------------------------------------------------
    def is_valid_hash(self, hashstr):
        return self._hash_re.match(hashstr)

    # --------------------------------------------------------------------------
    def cache(self, hashstr, data):
        CacheFile(hashstr).save(data)

        try:
            info = self._cached[hashstr]
            info["access_time"] = time.time()
            info["hits"] += 1
        except KeyError:
            self._cached[hashstr] = {
                "insert_time": time.time(),
                "access_time": time.time(),
                "hits": 1,
            }
            self.maintain()

    # --------------------------------------------------------------------------
    def is_cached(self, hashstr):
        try:
            info = self._cached[hashstr]
            info["access_time"] = time.time()
            info["hits"] += 1
            self._hits_count += 1
            self.maintain()
            return True
        except KeyError:
            self._miss_count += 1
            return False

    # --------------------------------------------------------------------------
    def _gather_values(self, getters):
        values = {}
        for key, getter in getters.items():
            try: value = getter()
            except Exception as error: value = str(error)

            if value is None:
                values[key] = "N/A"
            else:
                if type(value) is float:
                    values[key] = round(value, 2)
                else:
                    values[key] = value
        return values

    # --------------------------------------------------------------------------
    def get_info(self):
        return self._gather_values(self._info_getters)

    # --------------------------------------------------------------------------
    def get_stats(self):
        return self._gather_values(self._stat_getters)

    # --------------------------------------------------------------------------
    def stream_saved_stats(self):
        first = True
        if self._stats_path is not None and os.path.isdir(self._stats_path):
            for entry in sorted(
                os.scandir(self._stats_path),
                key=lambda e: e.name
            ):
                with gzip.open(entry.path, 'rt', encoding="utf8") as statf:
                    stats = json.load(statf)
                    for stat in stats:
                        if first:
                            yield '['
                            first = False
                        else:
                            yield ','
                        yield json.dumps(stat)
        if first:
            yield '['
        yield ']'

    # --------------------------------------------------------------------------
    def uptime_seconds(self):
        return time.time() - self._start_time

    # --------------------------------------------------------------------------
    def saved_stats_seconds_ago(self):
        return time.time() - self._stats_save_time

    # --------------------------------------------------------------------------
    def saved_seconds_ago(self):
        return time.time() - self._save_time

    # --------------------------------------------------------------------------
    def cleaned_seconds_ago(self):
        return time.time() - self._cleanup_time

    # --------------------------------------------------------------------------
    def save_path(self):
        return self._save_path

    # --------------------------------------------------------------------------
    @property
    def auth_key_writes(self):
        return self._auth_key_writes

    # --------------------------------------------------------------------------
    def save_file_size(self):
        try: return os.path.getsize(self.save_path())
        except: return 0

    # --------------------------------------------------------------------------
    def save_cache_size(self):
        size = 0

        d = ctcache_app.config["CACHE_FOLDER"]
        for f in os.listdir(d):
            absolute_path = os.path.join(d, f)
            if os.path.isfile(absolute_path):
                size += os.path.getsize(absolute_path)

        return size

    # --------------------------------------------------------------------------
    def static_path(self):
        return ctcache_app.get_static_folder()

    # --------------------------------------------------------------------------
    def cached_count(self):
        return len(self._cached)

    # --------------------------------------------------------------------------
    def cleaned_count(self):
        return self._cleaned_count

    # --------------------------------------------------------------------------
    def hit_count(self):
        return self._hits_count

    # --------------------------------------------------------------------------
    def miss_count(self):
        return self._miss_count

    # --------------------------------------------------------------------------
    def total_hit_rate(self):
        try:
            hits = sum(i["hits"] - 1 for h, i in self._cached.items())
            total = sum(i["hits"] for h, i in self._cached.items())
            return hits / total
        except ZeroDivisionError:
            return None

    # --------------------------------------------------------------------------
    def hit_rate(self):
        try:
            return self._hits_count / (self._hits_count + self._miss_count)
        except ZeroDivisionError:
            return None

    # --------------------------------------------------------------------------
    def miss_rate(self):
        try:
            return self._miss_count / (self._hits_count + self._miss_count)
        except ZeroDivisionError:
            return None

    # --------------------------------------------------------------------------
    def hit_count_histogram(self):
        result = dict()
        for hashstr, info in self._cached.items():
            try:
                hit_count = info["hits"]
                try:
                    result[hit_count] += 1
                except KeyError:
                    result[hit_count] = 1
            except: pass

        return result

    # --------------------------------------------------------------------------
    def age_days_histogram(self):
        result = dict()
        for hashstr, info in self._cached.items():
            try:
                try:
                    result[age_days] += 1
                except KeyError:
                    result[age_days] = 1
            except: pass

        return result

    # --------------------------------------------------------------------------
    def _format_time(self, s, pos=None):
        if s < 60:
            return "%ds" % (s)
        if s < 3600:
            return "%dm %ds" % (s / 60, s % 60)
        if s < 86400:
            return "%dh %dm" % (s / 3600, (s / 60) % 60)
        if s < 604800:
            return "%dd %dh" % (s / 86400, (s / 3600) % 24)
        return "%d [wk]" % (s / 604800)

    # --------------------------------------------------------------------------
    @staticmethod
    def _blend(lt, rt, f):
        return tuple(max(min(l * (1.0 - f) + r * f, 1), 0) for l, r in zip(lt, rt))
    # --------------------------------------------------------------------------
    def age_hits_scatter_img(self, imgfmt="svg"):

        data = {
            "insert": [],
            "access": [],
            "color": [],
            "alpha": [],
            "hits": []}

        now = time.time()
        l = len(self._cached)
        for hashstr, info in self._cached.items():
            try:
                if (now - info["access_time"]) >= 30:
                    data["insert"].append((now - info["insert_time"]))
                    data["access"].append((now - info["access_time"]))
                    data["color"].append(hash(hashstr) % l)
                    data["hits"].append(math.log(info["hits"])*10.0)
            except: pass

        tick_maj_loc = pltckr.LogLocator(base=60.0)
        tick_min_loc = pltckr.MultipleLocator(base=3600.0)
        tick_maj_fmt = pltckr.FuncFormatter(self._format_time)
        tick_min_fmt = pltckr.NullFormatter()

        fig, spl = plt.subplots()
        plt.style.use('dark_background')
        fig.set_size_inches(8, 5)
        spl.set_xscale("log")
        spl.set_yscale("log")
        spl.xaxis.set_minor_locator(tick_min_loc)
        spl.xaxis.set_major_locator(tick_maj_loc)
        spl.yaxis.set_minor_locator(tick_min_loc)
        spl.yaxis.set_major_locator(tick_maj_loc)
        spl.xaxis.set_minor_formatter(tick_min_fmt)
        spl.xaxis.set_major_formatter(tick_maj_fmt)
        spl.yaxis.set_minor_formatter(tick_min_fmt)
        spl.yaxis.set_major_formatter(tick_maj_fmt)
        spl.xaxis.set_tick_params(labelrotation=90)
        spl.set_ylabel("last access ago")
        spl.set_xlabel("inserted ago")
        spl.grid(which="both", axis="both", alpha=0.3)
        spl.scatter(
            x="insert",
            y="access",
            c="color",
            s="hits",
            data=data,
            label="Hit count")
        spl.legend()
        del data

        output = io.BytesIO()
        plt.savefig(
            output,
            transparent=True,
            bbox_inches="tight",
            format=imgfmt)
        fig.clear()
        plt.close(fig)
        output.seek(0)

        return output

    # --------------------------------------------------------------------------
    def total_hits_histogram_img(self, imgfmt="svg"):

        fig, spl = plt.subplots()
        plt.style.use('dark_background')
        fig.set_size_inches(5, 5)
        spl.yaxis.set_major_formatter(pltckr.ScalarFormatter())
        spl.xaxis.set_minor_locator(pltckr.NullLocator())
        spl.xaxis.set_major_locator(pltckr.MultipleLocator(1))
        spl.xaxis.set_tick_params(rotation=90,labelsize=8)

        hits_hist = self.hit_count_histogram()
        lc = (1.0, 0.3, 0.1)
        rc = (0.3, 1.0, 0.1)
        x = []
        y = []
        c = []

        def _reduced(maxlen):
            def _sum(x, y):
                return (min(x), max(x), sum(y))
            src = [(i, i*hits_hist.get(i, 0)) for i in range(max(hits_hist)+1)]
            slen = len(src)
            fact = int(math.ceil(slen / maxlen))
            nlen = int(math.ceil(slen / fact))
            for step in range(nlen):
                bgn = step*fact
                idx = [bgn + i for i in range(fact) if (bgn + i) < slen]
                yield _sum(*map(list, zip(*[src[i] for i in idx])))

        if hits_hist:
            hist_hits = _reduced(25)
            m = 100 #max(t[1] for t in hits_hist)
            for hmin, hmax, tcount in hist_hits:
                x.append("%d-%d" % (hmin, hmax) if hmin < hmax else "%d" % hmin)
                y.append(tcount)
                c.append(self._blend(lc, rc, float(hmax) / m if m > 0 else 0))

        spl.set_ylabel("total number of hits")
        spl.set_xlabel("number of hits")
        spl.grid(which="major", axis="y", alpha=0.2)
        spl.bar(x, y, color=c)

        output = io.BytesIO()
        plt.savefig(
            output,
            transparent=True,
            bbox_inches="tight",
            format=imgfmt)
        fig.clear()
        plt.close(fig)
        output.seek(0)

        return output

    # --------------------------------------------------------------------------
    def hits_histogram_img(self, imgfmt="svg"):

        fig, spl = plt.subplots()
        plt.style.use('dark_background')
        fig.set_size_inches(5, 5)
        spl.set_yscale("log")
        spl.yaxis.set_major_formatter(pltckr.ScalarFormatter())
        spl.xaxis.set_minor_locator(pltckr.NullLocator())
        spl.xaxis.set_major_locator(pltckr.MaxNLocator(integer=True, min_n_ticks=1))

        hits_hist = self.hit_count_histogram()
        lc = (1.0, 0.3, 0.1)
        rc = (0.3, 1.0, 0.1)
        x = []
        y = []
        c = []

        if hits_hist:
            m = max(hits_hist)
            for hits, count in hits_hist.items():
                x.append(hits)
                y.append(count)
                c.append(self._blend(lc, rc, float(hits-1) / m if m > 0 else 0))

        spl.set_ylabel("number of hashes")
        spl.set_xlabel("number of hits")
        spl.grid(which="major", axis="y", alpha=0.2)
        spl.bar(x, y, color=c)

        output = io.BytesIO()
        plt.savefig(
            output,
            transparent=True,
            bbox_inches="tight",
            format=imgfmt)
        fig.clear()
        plt.close(fig)
        output.seek(0)

        return output

    # --------------------------------------------------------------------------
    def days_histogram_img(self, imgfmt="svg"):

        fig, spl = plt.subplots()
        plt.style.use('dark_background')
        fig.set_size_inches(5, 5)
        spl.set_yscale("log")
        spl.yaxis.set_major_formatter(pltckr.ScalarFormatter())
        spl.xaxis.set_minor_locator(pltckr.NullLocator())
        spl.xaxis.set_major_locator(pltckr.MaxNLocator(integer=True, min_n_ticks=1))

        days_hist = self.age_days_histogram()
        lc = (1.0, 0.8, 0.1)
        rc = (0.3, 0.1, 0.8)
        x = []
        y = []
        c = []

        if days_hist:
            m = max(days_hist)
            for hits, count in days_hist.items():
                x.append(hits)
                y.append(count)
                c.append(self._blend(lc, rc, float(hits-1) / m if m > 0 else 0))

        spl.set_ylabel("number of hashes")
        spl.set_xlabel("number of days")
        spl.grid(which="major", axis="y", alpha=0.2)
        spl.bar(x, y, color=c)

        output = io.BytesIO()
        plt.savefig(
            output,
            transparent=True,
            bbox_inches="tight",
            format=imgfmt)
        fig.clear()
        plt.close(fig)
        output.seek(0)

        return output

# ------------------------------------------------------------------------------
@ctcache_app.route("/cache/<hashstr>", methods=['GET', 'PUT'])
def ctc_cache(hashstr):
    if not clang_tidy_cache.is_valid_hash(hashstr):
        return flask.abort(400)

    if flask.request.method == 'GET':
        if not clang_tidy_cache.is_cached(hashstr):
            flask.abort(404)

        try:
            return flask.send_from_directory(
                directory=ctcache_app.config["CACHE_FOLDER"],
                path=hashstr,
                download_name=hashstr,
                as_attachment=False
            )
        except FileNotFoundError:
            flask.abort(500)

    if flask.request.method == 'PUT':
        data = flask.request.form['data']
        clang_tidy_cache.cache(hashstr, data)
        return "true"

    return flask.abort(500)
# ------------------------------------------------------------------------------
@ctcache_app.route("/is_cached/<hashstr>")
def ctc_is_cached(hashstr):
    return "true" if clang_tidy_cache.is_cached(hashstr) else "false"
# ------------------------------------------------------------------------------
@ctcache_app.route("/purge_cache")
def ctc_purge_cache():
    # Deny GET if auth_key_writes is configured
    # In a future update this API can only be called with a DELETE HTTP method
    if flask.request.method != 'GET' and clang_tidy_cache.auth_key_writes:
        return flask.abort(403)
    return str(clang_tidy_cache.do_purge())
# ------------------------------------------------------------------------------
@ctcache_app.route("/stats/cached_count")
def ctc_status_cached_count():
    return str(clang_tidy_cache.cached_count())
# ------------------------------------------------------------------------------
@ctcache_app.route("/stats/cleaned_count")
def ctc_status_cleaned_count():
    return str(clang_tidy_cache.cleaned_count())
# ------------------------------------------------------------------------------
@ctcache_app.route("/stats/hit_count")
def ctc_status_hit_count():
    return str(clang_tidy_cache.hit_count())
# ------------------------------------------------------------------------------
@ctcache_app.route("/stats/miss_count")
def ctc_status_miss_count():
    return str(clang_tidy_cache.miss_count())
# ------------------------------------------------------------------------------
@ctcache_app.route("/stats/hit_rate")
def ctc_status_hit_rate():
    return str(clang_tidy_cache.hit_rate())
# ------------------------------------------------------------------------------
@ctcache_app.route("/stats/miss_rate")
def ctc_status_miss_rate():
    return str(clang_tidy_cache.miss_rate())
# ------------------------------------------------------------------------------
@ctcache_app.route("/info")
def ctc_info():
    return json.dumps(clang_tidy_cache.get_info())
# ------------------------------------------------------------------------------
@ctcache_app.route("/stats")
def ctc_stats():
    return json.dumps(clang_tidy_cache.get_stats())
# ------------------------------------------------------------------------------
@ctcache_app.route("/stats/ctcache.json")
def ctc_saved_stats():
    try:
        return flask.Response(
            clang_tidy_cache.stream_saved_stats(),
            mimetype="application/json")
    except Exception as error:
        return str(error)
# ------------------------------------------------------------------------------
@ctcache_app.route("/image/age_hits_scatter.svg")
def ctc_image_age_hits_scatter():
    try:
        return flask.send_file(
            clang_tidy_cache.age_hits_scatter_img(),
            mimetype="image/svg+xml")
    except Exception as error:
        return str(error)
# ------------------------------------------------------------------------------
@ctcache_app.route("/image/hits_histogram.svg")
def ctc_image_hits_histogram():
    try:
        return flask.send_file(
            clang_tidy_cache.hits_histogram_img(),
            mimetype="image/svg+xml")
    except Exception as error:
        return str(error)
# ------------------------------------------------------------------------------
@ctcache_app.route("/image/total_hits_histogram.svg")
def ctc_image_total_hits_histogram():
    try:
        return flask.send_file(
            clang_tidy_cache.total_hits_histogram_img(),
            mimetype="image/svg+xml")
    except Exception as error:
        return str(error)
# ------------------------------------------------------------------------------
@ctcache_app.route("/image/days_histogram.svg")
def ctc_image_age_histogram():
    try:
        return flask.send_file(
            clang_tidy_cache.days_histogram_img(),
            mimetype="image/svg+xml")
    except Exception as error:
        return str(error)
# ------------------------------------------------------------------------------
@ctcache_app.route("/static/<file_name>")
def ctc_static_file(file_name):
    try:
        return flask.send_from_directory(
            directory=ctcache_app.config["STATIC_FOLDER"],
            path=file_name,
            download_name=file_name,
            as_attachment=False)
    except FileNotFoundError:
        flask.abort(404)
# ------------------------------------------------------------------------------
@ctcache_app.route("/")
def ctc_server_root():
    return flask.redirect("/static/index.html", code=302)
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    argparser = get_argument_parser()
    options = argparser.parse_args()
    clang_tidy_cache = ClangTidyCache(options)
    if options.debug_mode:
        ctcache_app.run(
            debug=True,
            host="0.0.0.0",
            port=options.port_number)
    else:
        from gevent.pywsgi import WSGIServer
        srvr = WSGIServer(("0.0.0.0", options.port_number), ctcache_app)
        try: srvr.serve_forever()
        except KeyboardInterrupt:
            pass
# ------------------------------------------------------------------------------

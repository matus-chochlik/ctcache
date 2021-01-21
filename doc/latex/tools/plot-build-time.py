#!/usr/bin/python3 -B
# coding=utf8
# Copyright Matus Chochlik.
# Distributed under the Boost Software License, Version 1.0.
# See accompanying file LICENSE_1_0.txt or copy at
#  http://www.boost.org/LICENSE_1_0.txt
# ------------------------------------------------------------------------------
import os
import sys
import math
import matplotlib.pyplot as plt
import matplotlib.ticker as pltckr
import numpy as np
from statistics import mean

from common import DictObject, PresArgParser
# ------------------------------------------------------------------------------
class ArgParser(PresArgParser):
    # --------------------------------------------------------------------------
    def __init__(self, **kw):
        PresArgParser.__init__(self, **kw)

        self._add_single_input_arg()
# ------------------------------------------------------------------------------
def make_argparser():
    return ArgParser(prog=os.path.basename(__file__))
# ------------------------------------------------------------------------------
def _format_time(s, pos=None):
    if s >= 3600:
        h = int(s/3600)
        s -= h*3600
        m = int(s/60)
        s -= m*60
        return "%2d:%02d:%02d" % (h, m, s)

    m = int(s/60)
    s -= m*60
    return "%2d:%02d" % (m, s)
# ------------------------------------------------------------------------------
def do_plot(options):

    labels = {
        0: "compiler\nclang-tidy",
        1: "compiler\nctcache",
        2: "ccache\nclang-tidy",
        3: "ccache\nctcache"
    }
    data = {}
    stats = DictObject.loadJson(options.input_path)
    y_interval = 0.0

    for measured in stats.measurements:
        if measured.ctcache and measured.ctcache == False:
            continue
        key = (2 if measured.ccache else 0) + (1 if measured.ctcache else 0)
        try:
            dk = data[key]
        except KeyError:
            dk = data[key] = {
                "label": labels[key]
            } 
        try:
            dkj = dk["jobs"]
        except KeyError:
            dkj = dk["jobs"] = {}
        
        dkj[measured.jobs] = measured.time
        y_interval = max(y_interval, measured.time)

    tick_opts = [5,10,15,30,60]
    for t in tick_opts:
        y_tick_maj = t*60
        if y_interval / y_tick_maj < 12:
            break

    plt.style.use('dark_background')
    fig, spl = plt.subplots()
    options.initialize(plt, fig)

    cfgs = []
    times = {}
    for k, v in data.items():
        cfgs.append(v["label"])
        for j, t in v["jobs"].items():
            try:
                times[j].append(t)
            except:
                times[j] = [t]
    width = 1.0 / (len(times)+1)
    offs = [width * i for i in range(len(times))]
    offs = [o - (max(offs) - min(offs))/2 for o in offs]

    spl.yaxis.set_major_locator(pltckr.MultipleLocator(y_tick_maj))
    spl.yaxis.set_major_formatter(pltckr.FuncFormatter(_format_time))
    for o, (j, t) in zip(offs, times.items()):
        bins = [i+o for i in range(len(cfgs))]
        spl.bar(
            bins, t,
            width=width*0.8,
            tick_label=cfgs,
            label="-j %d" % j,
            color=options.color_by_jobs(j)
        )
    spl.set_ylabel("Build time")
    spl.grid(axis="y")
    spl.legend()

    options.finalize(plt)
# ------------------------------------------------------------------------------
def main():
    do_plot(make_argparser().make_options())
    return 0
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    exit(main())
# ------------------------------------------------------------------------------

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

        self._add_multi_input_arg()
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
        1: "ccache\nclang-tidy",
        2: "compiler\nctcache",
        3: "ccache\nctcache"
    }
    data = {}
    x_interval = 0.0

    for input_path in options.input_path:
        measured = DictObject.loadJson(input_path)
        key = (1 if measured.ccache else 0) + (2 if measured.ctcache else 0)
        try:
            dk = data[key]
        except KeyError:
            dk = data[key] = {
                "label": labels[key],
                "age": [],
                "load": []
            } 
        for row in measured.data:
            x_interval = max(x_interval, row.age)
            dk["age"].append(row.age)
            dk["load"].append(row.cpu_load_5)

    tick_opts = [5,10,15,30,60]
    for t in tick_opts:
        x_tick_maj = t*60
        if x_interval / x_tick_maj < 12:
            break

    plt.style.use('dark_background')
    fig, spl = plt.subplots()
    options.initialize(plt, fig)

    for k, dk in data.items():
        x = dk["age"]
        y = dk["load"]
        spl.plot(
            x, y,
            label=dk["label"],
            linewidth=2,
            color=options.color_from_to(k, 0, 3)
        )
 
    spl.xaxis.set_major_locator(pltckr.MultipleLocator(x_tick_maj))
    spl.xaxis.set_major_formatter(pltckr.FuncFormatter(_format_time))
    spl.set_xlabel("Build time")
    spl.set_ylabel("CPU load")
    spl.grid(axis="both", alpha=0.25)
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

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
def _format_mult(s, pos=None):
    return "%1.0fx" % s
# ------------------------------------------------------------------------------
def do_plot(options):

    data = {}

    for input_path in options.input_path:
        stats = DictObject.loadJson(input_path)
        try:
            d = data[stats.project_name]
        except KeyError:
            d = data[stats.project_name] = {}
        for measured in stats.measurements:
            try:
                dj = d[measured.jobs]
            except KeyError:
                dj = d[measured.jobs] = {}
            if measured.ccache and measured.ctcache:
                dj["cached"] = measured.time
            if not measured.ccache and not measured.ctcache:
                dj["uncached"] = measured.time

    plt.style.use('dark_background')
    fig, spl = plt.subplots()
    options.initialize(plt, fig)

    projects = []
    speedups = {}

    for k, v in data.items():
        projects.append(k)
        for j, t in v.items():
            try:
                sj = speedups[j]
            except KeyError:
                sj = speedups[j] = []
            try:
                sj.append(t["uncached"]/t["cached"])
            except:
                sj.append(0)

    width = 1.0 / (len(speedups)+1)
    offs = [width * i for i in range(len(speedups))]
    offs = [o - (max(offs) - min(offs))/2 for o in offs]

    spl.yaxis.set_major_formatter(pltckr.FuncFormatter(_format_mult))
    for o, (j, s) in zip(offs, speedups.items()):
        bins = [i+o for i in range(len(projects))]
        spl.bar(
            bins, s,
            width=width*0.8,
            tick_label=projects,
            label="-j %d" % j,
            color=options.color_by_jobs(j)
        )
    spl.set_ylabel("Speedup")
    spl.grid(axis="y", alpha=0.25)
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

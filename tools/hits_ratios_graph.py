#!/usr/bin/python3 -B
# coding=utf8
# Copyright (c) 2020 Matus Chochlik
# Distributed under the Boost Software License, Version 1.0.
# See accompanying file LICENSE_1_0.txt or copy at
#  http://www.boost.org/LICENSE_1_0.txt
# ------------------------------------------------------------------------------
# Data from http://ctcache:port/stats/ctcache.json can be used as input.

import os
import sys
import json
import math
import argparse
import matplotlib.pyplot as plt
# ------------------------------------------------------------------------------
class ArgParser(argparse.ArgumentParser):
    # --------------------------------------------------------------------------
    def _valid_pixdim(self, x):
        try:
            i = int(x)
            assert i > 16
            return i
        except:
            self.error("`%s' is not a valid frame size" % str(x))

    # --------------------------------------------------------------------------
    def _valid_bands(self, x):
        try:
            i = int(x)
            assert i > 1
            return i
        except:
            self.error("`%s' is not a valid number of bands " % str(x))

    # --------------------------------------------------------------------------
    def __init__(self, **kw):
        argparse.ArgumentParser.__init__(self, **kw)

        self.add_argument(
            '-i', '--input',
            metavar='INPUT-FILE',
            dest='input_path',
            nargs='?',
            type=os.path.realpath
        )

        self.add_argument(
            '-o', '--output',
            metavar='OUTPUT-FILE',
            dest='output_path',
            nargs='?',
            type=os.path.realpath,
            default="/tmp/ctcache.avi"
        )

        self.add_argument(
            '-W', '--width',
            metavar='NUMBER',
            dest='width',
            nargs='?',
            type=self._valid_pixdim,
            default=1200
        )

        self.add_argument(
            '-H', '--height',
            metavar='NUMBER',
            dest='height',
            nargs='?',
            type=self._valid_pixdim,
            default=800
        )

        self.add_argument(
            '-B', '--bands',
            metavar='NUMBER',
            dest='bands',
            nargs='?',
            type=self._valid_bands,
            default=None
        )

    # --------------------------------------------------------------------------
    def make_options(self):
        return self.parse_args()

# ------------------------------------------------------------------------------
def make_argparser():
    return ArgParser(prog=os.path.basename(__file__))

# ------------------------------------------------------------------------------
def render_chart(options):
    stats = json.load(open(options.input_path, "rt", encoding="utf8"))
    get_hist = lambda s: {int(k): v for k, v in s.get("hit_count_histogram", {}).items()}
    max_hits = int(max(max(get_hist(s).keys()) for s in stats))
    mh_norm = 1.0 / max_hits
    clamp = lambda t : tuple(max(min(x, 1), 0) for x in t)
    make_color = lambda a,b: clamp((math.sqrt(1.0-a)*b, math.sqrt(a)*b, 0.0))

    mh = range(max_hits)
    y = [[] for u in mh]

    if options.bands is not None:
        nb = options.bands
        b = [0.8 + 0.2 * math.sqrt((i+1) / nb) for i in range(nb)]
    else:
        b = [1.0]

    c = [make_color((i+1) * mh_norm, b[i % len(b)]) for i in mh]

    for stat in stats:
        hist = {k-1: k*v for k, v in get_hist(stat).items()}
        try:
            norm = 1.0 / sum(hist.values())
            for i in mh:
                y[i].append(hist.get(i, 0.0) * norm)
        except ZeroDivisionError:
            for i in mh:
                y[i].append(1.0 / max_hits)

    x = range(len(y[0]))

    plt.style.use('dark_background')
    fig, spl = plt.subplots()
    w_dpi = options.width/float(fig.dpi)
    h_dpi = options.height/float(fig.dpi)
    fig.set_size_inches(w_dpi, h_dpi)

    spl.set_xlabel("Time (non-linear)")
    spl.set_ylabel("Hit ratios")

    spl.stackplot(x, y, colors=c, edgecolors=(0.5, 0.5, 0.5), linewidth=0.0)
    
    plt.show()

# ------------------------------------------------------------------------------
def main():
    render_chart(make_argparser().make_options())
    return 0
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    exit(main())
# ------------------------------------------------------------------------------

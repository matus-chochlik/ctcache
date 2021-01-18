# Copyright Matus Chochlik.
# Distributed under the Boost Software License, Version 1.0.
# See accompanying file LICENSE_1_0.txt or copy at
#  http://www.boost.org/LICENSE_1_0.txt
# ------------------------------------------------------------------------------
import os
import gzip
import json
import argparse
# ------------------------------------------------------------------------------
class DictObject(object):
    # --------------------------------------------------------------------------
    def __init__(self, src):
        for k, v in src.items():
            self.__dict__[k] = DictObject.make(v)

    # --------------------------------------------------------------------------
    @classmethod
    def make(Class, src):
        if type(src) is dict:
            return Class(src)
        if type(src) is list:
            return [Class.make(e) for e in src]
        if type(src) is tuple:
            return (Class.make(e) for e in src)
        return src
    # --------------------------------------------------------------------------
    @classmethod
    def loadJson(Class, path):
        try:
            return Class.make(json.load(gzip.open(path, "rt")))
        except OSError:
            return Class.make(json.load(open(path, "rt")))
# ------------------------------------------------------------------------------
class PresArgParser(argparse.ArgumentParser):
    # --------------------------------------------------------------------------
    def _positive_int(self, x):
        try:
            i = int(x)
            assert(i > 0)
            return i
        except:
            self.error("`%s' is not a positive integer value" % str(x))
    # --------------------------------------------------------------------------
    def _add_single_input_arg(self):
        self.add_argument(
            '-i', '--input',
            metavar='INPUT-FILE',
            dest='input_path',
            nargs='?',
            type=os.path.realpath
        )
    # --------------------------------------------------------------------------
    def _add_multi_input_arg(self):
        self.add_argument(
            '-i', '--input',
            metavar='INPUT-FILE',
            dest='input_path',
            nargs='?',
            type=os.path.realpath,
            action="append"
        )
    # --------------------------------------------------------------------------
    def _add_jobs_arg(self):
        self.add_argument(
            '-j', '--jobs',
            metavar='COUNT',
            dest='job_count',
            nargs='?',
            default=1,
            type=self._positive_int
        )
    # --------------------------------------------------------------------------
    def __init__(self, **kw):
        argparse.ArgumentParser.__init__(self, **kw)

        self.add_argument(
            '-W', '--view',
            dest='viewer',
            default=False,
            action="store_true"
        )

        self.add_argument(
            '-o', '--output',
            metavar='OUTPUT-FILE',
            dest='output_path',
            nargs='?',
            type=os.path.realpath
        )
    # --------------------------------------------------------------------------
    def make_options(self):
        opts = self.parse_args()
        # ----------------------------------------------------------------------
        class _Options(object):
            # ------------------------------------------------------------------
            def __init__(self, base):
                self.__dict__.update(base.__dict__)
            # ------------------------------------------------------------------
            def initialize(self, plot, fig):
                if self.output_path:
                    fig.set_size_inches(8, 4.5)
            # ------------------------------------------------------------------
            def finalize(self, plot):
                if self.viewer:
                    plot.show()
                elif self.output_path:
                    plot.savefig(
                        self.output_path,
                        orientation="landscape",
                        transparent=True,
                        format="pdf"
                    )

        return _Options(opts)
# ------------------------------------------------------------------------------
def reduce_by(lst, fact, func = lambda l: float(sum(l))/len(l)):
    t = []
    r = []

    for e in lst:
        t.append(e)
        if len(t) >= fact:
            r.append(func(t))
            t = []

    try: r.append(func(t))
    except: pass
    return r
# ------------------------------------------------------------------------------

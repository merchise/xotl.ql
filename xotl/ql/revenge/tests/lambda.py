# lambda.py -- source test pattern for lambda functions
#
# This simple program is part of the decompyle test suite.
#
# decompyle is a Python byte-code decompiler
# See http://www.crazy-compilers.com/decompyle/ for
# for further information
from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)

palette = [(a,a,a) for a in range(256)]
palette = [chr(r_g_b[0])+chr(r_g_b[1])+chr(r_g_b[2]) for r_g_b in palette]
palette = [r for r in palette]

palette = lambda r_g_b1: r_g_b1[0]
palette = lambda r: r
palette = lambda r: r
palette = lambda r: r, palette

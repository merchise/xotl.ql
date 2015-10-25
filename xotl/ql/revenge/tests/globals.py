# globals.py -- test for global symbols
#
# This simple program is part of the decompyle test suite.
#
# decompyle is a Python byte-code decompiler
# See http://www.crazy-compilers.com/decompyle/ for
# for further information
from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)

def f():
    print(x)  # would result in a 'NameError' or 'UnboundLocalError'
    x = x+1
    print(x)

raise "This program can't be run"

x = 1
f()
print(x)

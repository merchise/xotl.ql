"""
test_global.py -- source test pattern for 'global' statement

This source is part of the decompyle test suite.

decompyle is a Python byte-code decompiler
See http://www.crazy-compilers.com/decompyle/ for
for further information
"""
from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)

i = 1; j = 7
def a():
    def b():
        def c():
            k = 34
            global i
            i = i+k
        l = 42
        c()
        global j
        j = j+l
    b()
    print(i, j) # should print 35, 49

a()
print(i, j)

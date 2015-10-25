"""
test_tuples.py -- source test pattern for tuples

This source is part of the decompyle test suite.

decompyle is a Python byte-code decompiler
See http://www.crazy-compilers.com/decompyle/ for
for further information
"""
from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)

a = (1,)
b = (2,3)
a,b = (1,2)
a,b = ( (1,2), (3,4,5) )

x = {}
try:
    x[1,2,3]
except:
    pass
x[1,2,3] = 42
print(x[1,2,3])
print(x[(1,2,3)])
assert x[(1,2,3)] == x[1,2,3]
del x[1,2,3]

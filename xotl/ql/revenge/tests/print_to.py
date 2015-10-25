"""
print_to.py -- source test pattern for 'print >> ...' statements

This source is part of the decompyle test suite.

decompyle is a Python byte-code decompiler
See http://www.crazy-compilers.com/decompyle/ for
for further information
"""
from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)

import sys

print(1,2,3,4,5, file=sys.stdout)

print(1,2,3,4,5, end=' ', file=sys.stdout)
print(file=sys.stdout)

print(1,2,3,4,5, end=' ', file=sys.stdout)
print(1,2,3,4,5, end=' ', file=sys.stdout)
print(file=sys.stdout)

print(file=sys.stdout)

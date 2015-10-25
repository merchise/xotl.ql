"""
test_integers.py -- source test pattern for integers

This source is part of the decompyle test suite.
Snippet taken from python libs's test_class.py

decompyle is a Python byte-code decompiler
See http://www.crazy-compilers.com/decompyle/ for
for further information
"""
from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)

import sys
#raise "This program can't be run"

i = 1
i = 42
i = -1
i = -42
i = sys.maxsize
minint = -sys.maxsize-1
print(sys.maxsize)
print(minint)
print(int(minint)-1)

print()
i = -2147483647   # == -maxint
print(i, repr(i))
i = i-1
print(i, repr(i))
i = -2147483648  # ==  minint   == -maxint-1
print(i, repr(i))
i = -2147483649  # ==  minint-1 == -maxint-2
print(i, repr(i))

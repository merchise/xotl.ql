# extendedPrint.py -- source test pattern for extended print statements
#
# This simple program is part of the decompyle test suite.
#
# decompyle is a Python byte-code decompiler
# See http://www.crazy-compilers.com/decompyle/ for
# for further information
from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)

import sys

print("Hello World", file=sys.stdout)
print(1,2,3, file=sys.stdout)
print(1,2,3, end=' ', file=sys.stdout)
print(file=sys.stdout)

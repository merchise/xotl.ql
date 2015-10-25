"""
test_loops.py -- source test pattern for loops

This source is part of the decompyle test suite.

decompyle is a Python byte-code decompiler
See http://www.crazy-compilers.com/decompyle/ for
for further information
"""
from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)

for i in range(10):
    if i == 3:
        continue
    if i == 5:
        break
    print(i, end=' ')
else:
    print('Else')
print()

for i in range(10):
    if i == 3:
        continue
    print(i, end=' ')
else:
    print('Else')


i = 0
while i < 10:
    i = i+1
    if i == 3:
        continue
    if i == 5:
        break
    print(i, end=' ')
else:
    print('Else')
print()

i = 0
while i < 10:
    i = i+1
    if i == 3:
        continue
    print(i, end=' ')
else:
    print('Else')

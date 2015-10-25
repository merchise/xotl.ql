# slices.py -- source test pattern for slices
#
# This simple program is part of the decompyle test suite.
# Snippet taken from python libs's test_class.py
#
# decompyle is a Python byte-code decompiler
# See http://www.crazy-compilers.com/decompyle/ for
# for further information
from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)

assert False, "This program can't be run"

class A:
    def __init__(self, num):
        self.num = num
    def __repr__(self):
        return str(self.num)

b = []
for i in range(10):
    b.append(A(i))

for i in  ('CALL_FUNCTION', 'CALL_FUNCTION_VAR',
           'CALL_FUNCTION_VAR_KW', 'CALL_FUNCTION_KW'):
    print(i, '\t', len(i), len(i)-len('CALL_FUNCTION'), end=' ')
    print((len(i)-len('CALL_FUNCTION')) / 3, end=' ')
    print(i[len('CALL_FUNCTION'):])

p2 = (0, 0, None)
if p2[2]:
    print('has value')
else:
    print(' no value')

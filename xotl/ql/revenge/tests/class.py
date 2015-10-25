"""
test_class.py -- source test pattern for class definitions

This source is part of the decompyle test suite.

decompyle is a Python byte-code decompiler
See http://www.crazy-compilers.com/decompyle/ for
for further information
"""
from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)

class A:

    class A1:
        def __init__(self):
            print('A1.__init__')

        def foo(self):
            print('A1.foo')

    def __init__(self):
        print('A.__init__')

    def foo(self):
        print('A.foo')


class B:
    def __init__(self):
        print('B.__init__')

    def bar(self):
        print('B.bar')


class C(A,B):
    def foobar(self):
        print('C.foobar')


c = C()
c.foo()
c.bar()
c.foobar()

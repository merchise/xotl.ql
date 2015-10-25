# test_nested_scopes.py -- source test pattern for nested scopes
#
# This source is part of the decompyle test suite.
#
# decompyle is a Python byte-code decompiler
# See http://www.crazy-compilers.com/decompyle/ for
# for further information
from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)



blurb = 1

def k0():
    def l0(m=1):
        print()
    l0()

def x0():
    def y0():
        print()
    y0()

def x1():
    def y1():
        print('y-blurb =', blurb)
    y1()

def x2():
    def y2():
        print()
    blurb = 2
    y2()

def x3a():
    def y3a(x):
        print('y-blurb =', blurb, flurb)
    print()
    blurb = 3
    flurb = 7
    y3a(1)
    print('x3a-blurb =', blurb)

def x3():
    def y3(x):
        def z():
            blurb = 25
            print('z-blurb =', blurb, end=' ')
        z()
        print('y-blurb =', blurb, end=' ')
    print()
    blurb = 3
    y3(1)
    print('x3-blurb =', blurb)

def x3b():
    def y3b(x):
        def z():
            print('z-blurb =', blurb, end=' ')
        blurb = 25
        z()
        print('y-blurb =', blurb, end=' ')
    print()
    blurb = 3
    y3b(1)
    print('x3-blurb =', blurb)

def x4():
    def y4(x):
        def z():
            print('z-blurb =', blurb)
        z()
    global blurb
    blurb = 3
    y4(1)

def x():
    def y(x):
        print('y-blurb =', blurb)
    blurb = 2
    y(1)


def func_with_tuple_args6(xxx_todo_changeme, xxx_todo_changeme1=(2, 3), *args, **kwargs):
    (a, b) = xxx_todo_changeme
    (c, d) = xxx_todo_changeme1
    def y(x):
        print('y-a =', a)
    print(c)

def find(self, name):
    # This is taken from 'What's new in Python 2.1' by amk
    L = list(filter(lambda x, name: x == name, self.list_attribute))

x0()
x1()
x2()
x3()
x3a()
x3b()
x4()
x()
print('blurb =', blurb)

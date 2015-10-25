# nested_elif.py -- source test pattern for nested elif
#
# This simple program is part of the decompyle test suite.
#
# decompyle is a Python byte-code decompiler
# See http://www.crazy-compilers.com/decompyle/ for
# for further information
from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)

a = None

if a == 1:
    print('1')
elif a == 2:
    print('2')

if a == 1:
    print('1')
elif a == 2:
    print('2')
else:
    print('other')

if a == 1:
    print('1')
elif a == 2:
    print('2')
elif a == 3:
    print('3')
else:
    print('other')

if a == 1:
    print('1')
elif a == 2:
    print('2')
elif a == 3:
    print('3')

if a == 1:
    print('1')
else:
    if a == 2:
        print('2')
    else:
        if a == 3:
            print('3')
        else:
            print('other')

if a == 1:
    print('1')
else:
    if a == 2:
        print('2')
    else:
        print('more')
        if a == 3:
            print('3')
        else:
            print('other')

if a == 1:
    print('1')
else:
    print('more')
    if a == 2:
        print('2')
    else:
        if a == 3:
            print('3')
        else:
            print('other')

if a == 1:
    print('1')
else:
    print('more')
    if a == 2:
        print('2')
    else:
        print('more')
        if a == 3:
            print('3')
        elif a == 4:
            print('4')
        elif a == 4:
            print('4')
        else:
            print('other')

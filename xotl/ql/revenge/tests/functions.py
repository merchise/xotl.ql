# test_functions.py -- source test pattern for functions
#
# This source is part of the decompyle test suite.
#
# decompyle is a Python byte-code decompiler
# See http://www.crazy-compilers.com/decompyle/ for
# for further information
from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)

def x0():
    pass

def x1(arg1):
    pass

def x2(arg1,arg2):
    pass

def x3a(*args):
    pass

def x3b(**kwargs):
    pass

def x3c(*args, **kwargs):
    pass

def x4a(foo, bar=1, bla=2, *args):
    pass

def x4b(foo, bar=1, bla=2, **kwargs):
    pass

def x4c(foo, bar=1, bla=2, *args, **kwargs):
    pass

def func_with_tuple_args(xxx_todo_changeme):
    (a,b) = xxx_todo_changeme
    print(a)
    print(b)

def func_with_tuple_args2(xxx_todo_changeme1, xxx_todo_changeme2):
    (a,b) = xxx_todo_changeme1
    (c,d) = xxx_todo_changeme2
    print(a)
    print(c)

def func_with_tuple_args3(xxx_todo_changeme3, xxx_todo_changeme4, *args):
    (a,b) = xxx_todo_changeme3
    (c,d) = xxx_todo_changeme4
    print(a)
    print(c)

def func_with_tuple_args4(xxx_todo_changeme5, xxx_todo_changeme6, **kwargs):
    (a,b) = xxx_todo_changeme5
    (c,d) = xxx_todo_changeme6
    print(a)
    print(c)

def func_with_tuple_args5(xxx_todo_changeme7, xxx_todo_changeme8, *args, **kwargs):
    (a,b) = xxx_todo_changeme7
    (c,d) = xxx_todo_changeme8
    print(a)
    print(c)

def func_with_tuple_args6(xxx_todo_changeme9, xxx_todo_changeme10=(2,3), *args, **kwargs):
    (a,b) = xxx_todo_changeme9
    (c,d) = xxx_todo_changeme10
    print(a)
    print(c)

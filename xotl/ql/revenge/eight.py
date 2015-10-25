# -*- encoding: utf-8 -*-
# ---------------------------------------------------------------------
# xotl.ql.revenge.eight
# ---------------------------------------------------------------------
# Copyright (c) 2014, 2015 Merchise Autrement and Contributors
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the LICENCE attached (see LICENCE file) in the distribution
# package.
#
# Created on 2014-04-08

'''Utility for defining methods variants.

Method variants allow several implementations of a single method to be chosen
given several conditions are met *when the module/class is being created*.
Notice this is not dynamic dispatching à la functional programming.


'''

from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)

import sys

from xoutil import types


# Python predicates
prepy27 = sys.version_info < (2, 7)
py27 = (2, 7) <= sys.version_info < (3, 0)
py30 = (3, 0) <= sys.version_info < (3, 1)
py31 = (3, 1) <= sys.version_info < (3, 2)
py32 = (3, 2) <= sys.version_info < (3, 3)
py33 = (3, 3) <= sys.version_info < (3, 4)
py34 = (3, 4) <= sys.version_info < (3, 5)
py35 = (3, 5) <= sys.version_info   # XXX: Not released as of today

py2k = py27 or prepy27
py3k = (3, 0) <= sys.version_info < (4, 0)


class unimplemented(object):
    '''Not implemented stub for `override`:func:.'''
    @staticmethod
    def override(pred):
        return override(pred=pred)

    def __init__(self, *args, **kwargs):
        raise TypeError


def override(pred=True, default=None):
    '''Allow overriding of `target`.

    If the predicated given by `pred` is True, the `target` is returned, but
    gains an `override` method to allowing chaining of overrides.

    The last defined `override` that matches `pred` wins.

    Intended usage::

        @override(py27)
        def foobar(x):
            print(x, 'Python 2.7')

        @foobar.override(prepy27)   # In python 2.7, keeps the previous def
        def foobar(x):
           print(x, 'An older python')

        @foobar.override(py30)
        def foobar(x):
            print(x, 'Python 3.0 but not bigger')

        @foobar.override(py3k)  # shadows the previous definition
        def foobar(x):
           print(x, 'Any python 3')


    .. warning:: This is not dynamic dispatching.  The predicated is evaluated
       only at function creation the returned function is thus, the variant
       that matched its predicate or the `unimplemented`:class: stub.

    '''
    def deco(target):
        def passed(p):
            if isinstance(p, types.FunctionType):
                result = p()
            else:
                result = p
            return result

        if passed(pred):
            target.override = lambda *a, **kw: override(default=target, *a, **kw)
            return target
        else:
            return default or unimplemented
    return deco

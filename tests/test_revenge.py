#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# ---------------------------------------------------------------------
# test_revenge
# ---------------------------------------------------------------------
# Copyright (c) 2015 Merchise Autrement and Contributors
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the LICENCE attached (see LICENCE file) in the distribution
# package.
#
# Created on 2015-10-25

from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)


def test_basic_uncompyler():
    from xotl.ql.revenge import Uncompyled

    def fib(n):
        a = b = 1
        while a < n:
            yield a
            a, b = b, a + b

    def fibl(n):
        return list(a for a in fib(n))

    u = Uncompyled(fib)
    assert u.source == ('a = b = 1\nwhile a < n:\n    '
                        'yield a\n    a, b = b, a + b')

    u = Uncompyled(fibl)
    assert u.source == 'return list((a for a in fib(n)))'

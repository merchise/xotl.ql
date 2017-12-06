#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------
# Copyright (c) Merchise Autrement [~º/~] and Contributors
# All rights reserved.
#
# This is free software; you can do what the LICENCE file allows you to.
#

from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)


from xotl.ql.tools import detect_names


def test_freenames_detection_1():
    result = detect_names('all(x for x in this for y in those if p(y)'
                          '      for z in y)')
    expected = {'this', 'those', 'p', 'all'}
    assert result == expected


def test_freenames_detection_2():
    result = detect_names('(lambda x: lambda p, y=p(x): x + y)(x)')
    expected = {'p', 'x'}  # p is the free var at y=p(x), not the lambda arg.
    assert result == expected

    # The same test but make it clear that, the free `p` (here `f`) is not the
    # same as the arg.
    result = detect_names('(lambda x: lambda p, y=f(x): x + y)(x)')
    expected = {'f', 'x'}
    assert result == expected

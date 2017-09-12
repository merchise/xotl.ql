#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# ---------------------------------------------------------------------
# test_tools
# ---------------------------------------------------------------------
# Copyright (c) 2015-2017 Merchise Autrement and Contributors
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the LICENCE attached (see LICENCE file) in the distribution
# package.
#
# Created on 2015-11-17


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

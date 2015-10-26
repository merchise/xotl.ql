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

import pytest
import sys
_py3 = sys.version_info >= (3, 0)
del sys


@pytest.mark.xfail(_py3, reason='Still not running on Py3k')
def test_ifexpression():
    from xotl.ql.revenge import Uncompyled
    l = lambda x, y: x if x else y
    u = Uncompyled(l)
    assert u.source == 'if x:\n    return x\nreturn y'


def test_lambda():
    from xotl.ql.revenge import Uncompyled
    l = lambda: lambda x, y, a=1, *args, **kwargs: x + y + a
    u = Uncompyled(l)
    assert u.source == 'return lambda x, y, a=1, *args, **kwargs: x + y + a'

    u = Uncompyled(l())
    assert u.source == 'return x + y + a'


def test_expressions():
    from xotl.ql.revenge import Uncompyled

    expressions = [
        'a + b',
        '[a for a in x if a < y]',
        '(a for a in this if a < y)',
        '{k: v for k, v in this}',
        '{s for s in this if s < y}'
    ]
    codes = [(compile(expr, '<test>', 'eval'), expr) for expr in expressions]
    failures = []
    for code, expr in codes:
        u = Uncompyled(code)
        if u.source != 'return ' + expr:
            failures.append((expr, u.source))
    assert not failures

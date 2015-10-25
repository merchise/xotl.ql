#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# ---------------------------------------------------------------------
# xotl.ql.tests.test_this
# ---------------------------------------------------------------------
# Copyright (c) 2012-2015 Merchise Autrement
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under
# the terms of the LICENCE attached in the distribution package.
#
# Created on May 25, 2012

from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        unicode_literals as _py3_unicode,
                        absolute_import as _py3_abs_import)


def test_this_uniqueness():
    from xotl.ql import this
    from xotl.ql.core import universe

    assert this is universe()
    assert this is this.whatever
    assert this is this[:90]


def test_this_iterable():
    from xotl.ql import this
    try:
        iter(this)
    except TypeError:
        assert False, 'this should be iterable'


def test_queries():
    from xotl.ql import this
    # Test that no error happens at the query expression definition time.
    (e for e in this)
    ((x for x in e) for e in this)
    (e for e in (x for x in this))
    (e for e in this if e(y for y in this))
    (e for e in this if any(x for x in e))
    (x for x, y in this)

    # Rather invalid but syntactically correct in Python
    (x for x[1] in this)     # noqa
    (x for x.y in this)      # noqa

    # Invalid in Python syntax
    try:
        eval('(x for x + 1 in this)')
    except SyntaxError:
        pass
    else:
        assert False, 'In Python you cannot assign to an expression'

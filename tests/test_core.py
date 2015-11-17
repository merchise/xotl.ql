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

from xotl.ql.core import this, Universe, normalize_query


def test_this_uniqueness():
    assert this is Universe()
    assert this is this.whatever
    assert this is this[:90]


def test_this_iterable():
    try:
        iter(this)
    except TypeError:
        assert False, 'this should be iterable'


def _build_test(generator):
    def test_expr():
        query = normalize_query(generator)
        assert query.qst


def _inject_tests(expressions, fmt, mark=lambda x: x):
    for index, expr in enumerate(expressions):
        test = mark(_build_test(expr))
        globals()[fmt % index] = test


QUERIES = [
    (e for e in this),
    ((x for x in e) for e in this),
    (e for e in (x for x in this)),
    (e for e in this if e(y for y in this)),
    (e for e in this if any(x for x in e)),
    (x for x, y in this),
    (x for x[1] in this),     # noqa
    (x for x.y in this),      # noqa
]
_inject_tests(QUERIES, 'test_query_%d')

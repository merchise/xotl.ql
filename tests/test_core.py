#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# ---------------------------------------------------------------------
# xotl.ql.tests.test_this
# ---------------------------------------------------------------------
# Copyright (c) 2012-2016 Merchise Autrement
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

from xoutil import Unset
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


def _build_test(generator, names=None):
    def test_expr():
        query = normalize_query(generator)
        assert query.qst
        if names:
            for name, val in names.items():
                if val is not Unset:
                    val = query.get_name(name)
                else:
                    try:
                        query.get_name(name)
                    except:
                        raise
                    else:
                        pass


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


global_sentinel = 12


def test_names():
    from xotl.ql.core import get_predicate_object, normalize_query, this

    def f(a=100):
        return lambda y: global_sentinel < y < a

    pred = get_predicate_object(f())
    assert pred.qst
    assert pred.get_name('a') == 100

    # Test that globals may change
    global global_sentinel
    assert pred.get_name('global_sentinel') == global_sentinel
    global_sentinel = 90
    assert pred.get_name('global_sentinel') == global_sentinel

    try:
        get_predicate_object(f)
    except:
        pass  # not an expression
    else:
        assert False

    q = normalize_query(x for x in this)
    assert q.get_name('.0') is this
    assert '.0' in q.names

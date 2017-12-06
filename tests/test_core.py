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


def test_queries():
    queries = [
        (e for e in this),
        ((x for x in e) for e in this),
        (e for e in (x for x in this)),
        (e for e in this if e(y for y in this)),
        (e for e in this if any(x for x in e)),
        (x for x, y in this),
        (x for x[1] in this),     # noqa
        (x for x.y in this),      # noqa
    ]
    for generator in queries:
        query = normalize_query(generator)
        assert query.qst


global_sentinel = 12


def test_names():
    from xotl.ql.core import get_predicate_object, normalize_query, this

    def f(a=100):
        return lambda y: global_sentinel < y < a

    pred = get_predicate_object(f())
    assert pred.qst
    assert pred.get_value('a') == 100

    # Test that globals may change
    global global_sentinel
    assert pred.get_value('global_sentinel') == global_sentinel
    global_sentinel = 90
    assert pred.get_value('global_sentinel') == global_sentinel

    try:
        get_predicate_object(f)
    except Exception:
        pass  # not an expression
    else:
        assert False

    q = normalize_query(x for x in this)
    assert q.get_value('.0') is this
    assert '.0' in q.locals
    assert 'x' not in q.locals
    assert 'global_sentinel' in q.globals
    assert '1qwwee' not in q.globals

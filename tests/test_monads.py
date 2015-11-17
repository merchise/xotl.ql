#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# ---------------------------------------------------------------------
# test_monads
# ---------------------------------------------------------------------
# Copyright (c) 2015 Merchise Autrement and Contributors
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the LICENCE attached (see LICENCE file) in the distribution
# package.
#
# Created on 2015-10-19


from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)


from xoutil import Undefined
from xotl.ql.translation._monads import Empty, Join, Map, Unit, Cons, Foldr


def test_empty():
    assert not isinstance(Undefined, Empty), \
        'Undefined is NOT an Empty collection'
    assert Empty() is Empty(), 'Empty should be a singleton'
    assert isinstance(Empty(), Empty), 'Empty() is an Empty collection'


def test_simple_query():
    # (x for x in this if predicate(x))
    this = Cons(1, list(range(2, 50)))
    predicate = lambda x: x % 2 == 0
    query = Join(Map(lambda x: Unit(x) if predicate(x) else Empty())(this))
    result = query()  # execute the query naively
    assert result.aslist() == [x for x in range(1, 50) if predicate(x)]


def test_foldr():
    from functools import reduce
    import operator
    assert reduce(operator.add, Cons(1, [2]).asiter(), 0) == 3
    assert Foldr(operator.add, 0, Cons(1, [2]))() == 3
    assert reduce(Foldr(operator.add), Cons(1, [2])) == 3

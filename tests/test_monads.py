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

import pytest
import operator
from xoutil.symbols import Undefined
from xotl.ql.translation.monads import (
    Empty, Join, Map, Unit, Cons, Foldr,
    LazyCons, SortedCons, Intersection, Union
)

from hypothesis import given, strategies as s, example

import sys
_py3 = sys.version_info >= (3, 0)

small_sets = s.sets(s.integers(min_value=0, max_value=100),
                    min_size=1, max_size=4)


@given(small_sets, small_sets)
@example([1, 2], [2, 1])
def test_intersection(i1, i2):
    s1 = list(i1)
    s2 = list(i2)
    c1 = Cons(s1[0], s1[1:])
    c2 = Cons(s2[0], s2[1:])
    i = Intersection(c1, c2)()
    assert c1.set() & c2.set() == i.set()


@given(small_sets, small_sets)
def test_union(i1, i2):
    s1 = list(i1)
    s2 = list(i2)
    c1 = Cons(s1[0], s1[1:])
    c2 = Cons(s2[0], s2[1:])
    u = Union(c1, c2)()
    assert c1.set() | c2.set() == u.set()


def test_empty():
    assert not isinstance(Undefined, Empty), \
        'Undefined is NOT an Empty collection'
    assert Empty() is Empty(), 'Empty should be a singleton'
    assert isinstance(Empty(), Empty), 'Empty() is an Empty collection'


def test_interating_partial_cons_should_fail():
    for ConsType in (LazyCons, Cons):
        A1 = ConsType(1)
        with pytest.raises(TypeError):
            head, tail = A1


def test_simple_query():
    # (x for x in this if predicate(x))
    this = Cons(1, list(range(2, 50)))
    predicate = lambda x: x % 2 == 0
    query = Join(Map(lambda x: Unit(x) if predicate(x) else Empty())(this))
    result = query()  # execute the query naively
    assert result.list() == [x for x in range(1, 50) if predicate(x)]


def test_foldr():
    from functools import reduce
    import operator
    assert reduce(operator.add, Cons(1, [2]).iter(), 0) == 3
    assert Foldr(operator.add, 0, Cons(1, [2]))() == 3
    assert reduce(Foldr(operator.add), Cons(1, [2])) == 3


def test_mc_routine_1():
    from xotl.ql import qst
    from xotl.ql.revenge.qst import Name, IfExp, Load, Lambda
    from xotl.ql.translation.monads import (
        translate,
        _make_arguments,
        Join,
        Map,
        Empty,
        Unit,
        Cons
    )
    genexpr = qst.parse('(x for x in this if predicate(x))')
    # MC [x | x <- this, predicate(x)]
    # = Join(Map(lambda x: Unit(x) if predicate(x) else Empty())(this))
    expected = Call(
        Name('join', Load()),
        Call(
            Call(
                Name('map', Load()),
                Lambda(
                    _make_arguments('x'),
                    IfExp(
                        Call(Name('predicate', Load()), Name('x', Load())),
                        Call(Name('unit', Load()), Name('x', Load())),
                        Call(Name('empty', Load()))
                    )
                )
            ),
            Name('this', Load())
        )
    )
    result = translate(genexpr, map='map', join='join', zero='empty',
                       unit='unit')
    assert result.body == expected

    predicate = lambda x: 's' in x
    this = Cons('I should be in the result', ['But I cannot be'])
    res = eval(compile(result, '', 'eval'),
               {'this': this, 'predicate': predicate, 'join': Join,
                'map': Map, 'empty': Empty, 'unit': Unit})
    assert res().list() == ['I should be in the result']


def test_mc_routine_2():
    from xotl.ql import qst
    from xotl.ql.revenge.qst import Name, Load, Lambda
    from xotl.ql.translation.monads import translate, _make_arguments
    genexpr = qst.parse('(x for x in this)')
    # MC [x | x <- this] = Map(lambda x: x)(this)
    expected = Call(
        Call(
            Name('Map', Load()),
            Lambda(_make_arguments('x'),
                   Name('x', Load()))
        ),
        Name('this', Load())
    )
    result = translate(genexpr)
    assert result.body == expected

    this = Cons('I should be in the result', ['And me too'])
    res = eval(compile(result, '', 'eval'),
               {'this': this, 'Join': Join,
                'Map': Map, 'Empty': Empty, 'Unit': Unit})().list()
    assert res == ['I should be in the result', 'And me too']


def test_mc_routine_4():
    from xotl.ql import qst
    from xotl.ql.revenge.qst import Name, Load, Lambda, Compare, In, Str
    from xotl.ql.translation.monads import translate, _make_arguments
    genexpr = qst.parse('all("s" in x for x in this)')
    # MC all(["s" in x | x <- this]) = all(Map(lambda x: 's' in x)(this))
    expected = Call(
        Name('all', Load()),
        Call(
            Call(
                Name('Map', Load()),
                Lambda(
                    _make_arguments('x'),
                    Compare(
                        Str('s'), [In()], [Name('x', Load())]
                    )
                )
            ),
            Name('this', Load())
        )
    )
    result = translate(genexpr)
    assert result.body == expected

    # Map returns a Cons and Cons iters yielding x, xs not the items.  To
    # compile this we must make all a foldr, that easily defined by
    # 'Foldr(operator.and, True)'.  All the same 'any' is 'Foldr(operator.or_,
    # False)', 'sum' is 'Foldr(operator.add, 0)', etc...

    this = Cons('Yes!!', ['No!!'])
    res = eval(compile(result, '', 'eval'),
               {'this': this, 'Join': Join,
                'all': Foldr(operator.and_, True),
                'Map': Map, 'Empty': Empty, 'Unit': Unit})
    assert res is False

    this = Empty()
    res = eval(compile(result, '', 'eval'),
               {'this': this, 'Join': Join,
                'all': Foldr(operator.and_, True),
                'Map': Map, 'Empty': Empty, 'Unit': Unit})
    assert res is True

    this = Cons('Yes!!!', Empty())
    res = eval(compile(result, '', 'eval'),
               {'this': this, 'Join': Join,
                'all': Foldr(operator.and_, True),
                'Map': Map, 'Empty': Empty, 'Unit': Unit})
    assert res is True


def test_mc_routine_5():
    from xotl.ql import qst
    from xotl.ql.translation.monads import translate
    this = list(range(10, 15)) + list(range(5, 10))
    genexpr = qst.parse('(x for x in this if 7 < x < 13)')
    result = translate(genexpr)
    # In this test, we won't use our implementation of the monadic functions
    # but translate them directly to Python.
    res = eval(compile(result, '', 'eval'),
               {'this': this,
                'Join': lambda x: [i for b in x for i in b],
                'Map': lambda f: lambda x: [f(i) for i in x],
                'Empty': lambda: [],
                'Unit': lambda x: [x]})
    assert res == [10, 11, 12, 8, 9]

    genexpr = qst.parse('sorted(x for x in this if 7 < x < 13)')
    result = translate(genexpr)
    # In this test, we won't use our implementation of the monadic functions
    # but translate them directly to Python.
    res = eval(compile(result, '', 'eval'),
               {'this': this,
                'Join': lambda x: [i for b in x for i in b],
                'Map': lambda f: lambda x: [f(i) for i in x],
                'Empty': lambda: [],
                'Unit': lambda x: [x]})
    assert res == [8, 9, 10, 11, 12]


def test_partial_sortedcons():
    c = SortedCons('<', 1)
    with pytest.raises(TypeError):
        head, tail = c

    head, tail = c(Empty())
    assert head == 1 and isinstance(tail, Empty)


# helpers


def Call(f, a=None):
    from xotl.ql import qst
    if a:
        return qst.Call(f, [a], [])
    else:
        return qst.Call(f, [], [])

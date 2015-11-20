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

import sys
_py3 = sys.version_info >= (3, 0)

import operator
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


def test_mc_routine_1():
    from xotl.ql import qst
    from xotl.ql.revenge.qst import Name, IfExp, Load, Lambda
    from xotl.ql.translation._monads import (
        _mc, _make_arguments, Join, Map, Empty, Unit, Cons)
    genexpr = qst.parse('(x for x in this if predicate(x))')
    # MC [x | x <- this, predicate(x)]
    # = Join(Map(lambda x: Unit(x) if predicate(x) else Empty())(this))
    expected = Call(
        Name('Join', Load()),
        Call(
            Call(
                Name('Map', Load()),
                Lambda(
                    _make_arguments('x'),
                    IfExp(
                        Call(Name('predicate', Load()), Name('x', Load())),
                        Call(Name('Unit', Load()), Name('x', Load())),
                        Call(Name('Empty', Load()))
                    )
                )
            ),
            Name('this', Load())
        )
    )
    result = _mc(genexpr)
    try:
        assert result.body == expected
    except:
        print(result)
        print(expected)
        raise

    predicate = lambda x: 's' in x
    this = Cons('I should be in the result', ['But I cannot be'])
    res = eval(compile(result, '', 'eval'),
               {'this': this, 'predicate': predicate, 'Join': Join,
                'Map': Map, 'Empty': Empty, 'Unit': Unit})
    assert res().aslist() == ['I should be in the result']


def test_mc_routine_2():
    from xotl.ql import qst
    from xotl.ql.revenge.qst import Name, Load, Lambda
    from xotl.ql.translation._monads import _mc, _make_arguments
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
    result = _mc(genexpr)
    try:
        assert result.body == expected
    except:
        print(result)
        print(expected)
        raise

    this = Cons('I should be in the result', ['And me too'])
    res = eval(compile(result, '', 'eval'),
               {'this': this, 'Join': Join,
                'Map': Map, 'Empty': Empty, 'Unit': Unit})().aslist()
    assert res == ['I should be in the result', 'And me too']


def test_mc_routine_4():
    from xotl.ql import qst
    from xotl.ql.revenge.qst import Name, Load, Lambda, Compare, In, Str
    from xotl.ql.translation._monads import _mc, _make_arguments
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
    result = _mc(genexpr)
    try:
        assert result.body == expected
    except:
        print(result.body)
        print(expected)
        assert str(result) == str(expected)
        raise

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


def Call(f, a=None):
    from xotl.ql import qst
    if a:
        return qst.Call(f, [a], [], None, None)
    else:
        return qst.Call(f, [], [], None, None)
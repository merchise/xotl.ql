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
                        absolute_import as _py3_abs_imports)

import pytest

from xotl.ql.core import this
from xotl.ql.translation.py import _TestPlan as translate

from xotl.ql.translation.monads import (
    # Rename so that names does not clash with internal names in the
    # monadic plan in the test plan 'translate'.
    Join as _Join,
    Map as _Map,
    Unit as _Unit,
    Empty as _Empty,
    Cons as _Cons
)

from .model import Person, Entity
from .world import elsa, papi, manolito, denia, pedro, cuba, havana, yade
from .world import manu


#
# You should notice that the translation.py module is NOT considered to be
# a production module, but a proof of concept for translation from xotl.ql
# as a language.
#
def test_nested_genexprs_with_thesefy():
    from xotl.ql.revenge import Uncompyled

    expected = (p for p in (x for x in this if isinstance(x, Person)))
    expected_uncomp = Uncompyled(expected)

    outer = (p for p in Person)
    outer_uncomp = Uncompyled(outer)
    assert outer_uncomp.qst == expected_uncomp.qst


def test_all_pred(**kwargs):
    plan1 = translate(
        (parent
         for parent in this
         if isinstance(parent, Person)
         if parent.children),
        **kwargs
    )
    result1 = set(plan1())
    assert elsa in result1
    assert papi in result1
    assert manolito not in result1
    assert result1 == set(plan1()), 'Plan should be reusable'

    plan2 = translate(
        (parent
         for parent in (x for x in this if isinstance(x, Person))
         if parent.children),
        **kwargs
    )
    result2 = set(plan2())
    assert elsa in result2
    assert papi in result2
    assert manolito not in result2

    plan3 = translate(
        (parent
         for parent in Person
         if parent.children),
        **kwargs
    )
    result3 = set(plan3())

    assert result1 == result2 == result3

    plan = translate(
        (parent
         for parent in Person
         if parent.children
         if sum(child.age for child in parent.children) > 60),
        **kwargs
    )
    result = list(plan())
    assert denia in result
    assert pedro in result
    assert len(result) == 2


@pytest.mark.xfail()
def test_full_monad_plan():
    test_all_pred(use_own_monads=True)


def test_real_plan():
    plan = _Join(
        _Join(
            # function call like map(f)(collection)
            (_Map(lambda parent:
                  _Unit(_Unit(parent) if parent.children else _Empty())
                  if isinstance(parent, Person) else _Empty()))
            (
                # in the real generated this is the name '.0'
                _Cons(manu, [manolito, cuba, havana])
            )
        )
    )
    try:
        plan()
    except Exception as error:
        failed = True
    else:
        error = None
        failed = False

    plan1 = translate(
        (parent
         for parent in _Cons(manu, [manolito, cuba, havana])
         if isinstance(parent, Person)
         if parent.children),
        use_own_monads=True
    )
    try:
        plan1()
    except:  # noqa
        if not failed:
            plan1.explain()
            raise
    else:
        if failed:
            plan1.explain()
            raise error

    plan2 = translate(
        (parent
         for parent in this
         if isinstance(parent, Person)
         if parent.children),
        use_own_monads=True
    )
    try:
        plan2()
    except RuntimeError:
        # RuntimeError: maximum recursion depth exceeded
        pass
    except:  # noqa
        if not failed:
            plan2.explain()
            raise
    else:
        if failed:
            plan2.explain()
            raise error


def test_naive_plan_no_join():
    plan = translate(
        who
        for who in Entity
        if who.name.startswith('Manuel')
    )
    result = list(plan())
    assert manu in result
    assert manolito in result
    assert yade not in result


@pytest.mark.xfail()
def test_itertools_with_this():
    enumerated = translate(
        (index, who) for (index, who) in enumerate(this)
        if isinstance(who, Person) and who.name.startswith('Manuel')
    )
    result = set(enumerated)
    assert result

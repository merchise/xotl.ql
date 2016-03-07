#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# ---------------------------------------------------------------------
# xotl.ql.tests.test_translate
# ---------------------------------------------------------------------
# Copyright (c) 2013-2016 Merchise Autrement and Contributors
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under
# the terms of the LICENCE attached in the distribution package.
#
# Created on 2013-01-29

from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_imports)

import pytest

from xotl.ql.core import this
from xotl.ql.core import get_query_object
from xotl.ql.translation.py import _TestPlan as translate

from .model import Person, Entity
from .world import *    # noqa


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


def test_naive_plan_no_join():
    select_old_entities = get_query_object(
        who
        for who in Entity
        if who.name.startswith('Manuel')
    )
    plan = translate(select_old_entities)
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

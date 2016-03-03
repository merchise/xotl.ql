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

from .metamodel import get_birth_date
from .model import Person, Place

from xotl.ql.core import this
from xotl.ql.core import get_query_object
from xotl.ql.translation.py import _TestPlan


# TODO:  Make this fixtures
cuba = Place(name='Cuba', type='Country')
havana = Place(name='Havana', type='Province', located_in=cuba)
lisa = Place(name='La lisa', type='Municipality', located_in=havana)
cotorro = Place(name='Cotorro', type='Municipality', located_in=havana)
ciego = Place(name='Ciego de Ávila', type='Province', located_in=cuba)
moron = Place(name='Morón', type='Municipality', located_in=ciego)


elsa = Person(name='Elsa Acosta Cabrera',
              birthdate=get_birth_date(65),
              lives_in=moron)

papi = Person(name='Manuel Vázquez Portal',
              birthdate=get_birth_date(63))

manu = Person(name='Manuel Vázquez Acosta',
              birthdate=get_birth_date(34),
              mother=elsa,
              father=papi,
              lives_in=lisa)

denia = Person(name='Ana Denia Pérez',
               birthdate=get_birth_date(58),
               lives_in=cotorro)

pedro = Person(name='Pedro Piñero',
               birthdate=get_birth_date(60),
               lives_in=cotorro)

yade = Person(name='Yadenis Piñero Pérez',
              birthdate=get_birth_date(33),
              mother=denia,
              father=pedro, lives_in=lisa)

ppp = Person(name='Yobanis Piñero Pérez',
             birthdate=get_birth_date(36),
             mother=denia,
             father=pedro,
             lives_in=lisa)

pedri = Person(name='Pedrito',
               birthdate=get_birth_date(10),
               father=ppp)

carli = Person(name='Carli',
               birthdate=get_birth_date(8),
               father=ppp)

manolito = Person(name='Manuel Vázquez Piñero',
                  birthdate=get_birth_date(6),
                  mother=yade,
                  father=manu,
                  lives_in=lisa)


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

    # Although semantically equiv, some sort of unimplemented transformation
    # of the previous is needed.
    # another = (p for p in this if isinstance(p, Person))


def test_all_pred():
    query = get_query_object(
        parent
        for parent in this
        if isinstance(parent, Person)
        if parent.children
    )
    plan1 = _TestPlan(query)
    result1 = set(plan1())
    assert elsa in result1
    assert papi in result1
    assert manolito not in result1
    assert result1 == set(plan1()), 'Plan should be reusable'

    query = get_query_object(
        parent
        for parent in (x for x in this if isinstance(x, Person))
        if parent.children
    )
    plan2 = _TestPlan(query)
    result2 = set(plan2())
    assert elsa in result2
    assert papi in result2
    assert manolito not in result2

    query = get_query_object(
        parent
        for parent in Person
        if parent.children
    )
    plan3 = _TestPlan(query)
    result3 = set(plan3())

    assert result1 == result2 == result3

    query = get_query_object(
        parent
        for parent in Person
        if parent.children
        if sum(child.age for child in parent.children) > 60
    )
    plan = _TestPlan(query)
    result = list(plan())
    assert denia in result
    assert pedro in result
    assert len(result) == 2

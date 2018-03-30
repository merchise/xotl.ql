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


from .metamodel import TransitiveRelationDescriptor, backref
from .metamodel import get_age, get_birth_date


def test_transitive():
    class Place:
        located_in = TransitiveRelationDescriptor('located_in')

        def __init__(self, **kwargs):
            for attr, val in kwargs.items():
                setattr(self, attr, val)

        def __repr__(self):
            return '<Place %r>' % self.name

    Place.located_in.target = Place

    cuba = Place(name='Cuba', located_in=None)
    havana = Place(name='Havana', located_in=cuba)
    plaza = Place(name='Plaza', located_in=havana)
    vedado = Place(name='Vedado', located_in=plaza)

    assert all(x in vedado.located_in for x in (cuba, havana, plaza))
    assert vedado not in vedado.located_in
    assert not cuba.located_in
    # After removing Havana from Cuba, Vedado is no longer in Cuba as well.
    del havana.located_in
    assert cuba not in vedado.located_in


def test_backref():
    class Person:
        mother = backref('mother', 'children')
        father = backref('father', 'children')

        def __init__(self, **kwargs):
            for attr, val in kwargs.items():
                setattr(self, attr, val)

        def __repr__(self):
            return '<Place %r>' % self.name

    Person.mother.target = Person
    Person.father.target = Person

    mami = Person(name='Elsa Acosta Cabrera')
    papi = Person(name='Manuel Vazquez Portal')
    manu = Person(name='Manuel Vazquez Acosta', mother=mami, father=papi)
    taire = Person(name='Tairelsy Vazquez Acosta', mother=mami, father=papi)
    yade = Person(name='Yadenis P')
    manolito = Person(name='Manolito Vazquez P', mother=yade, father=manu)

    assert manolito in yade.children and manolito in manu.children
    assert taire in mami.children and manu in mami.children


def test_ages():
    import random
    ages = range(4, 80)
    ages_seq = (random.choice(ages) for _ in range(100))
    assert all(get_age(get_birth_date(x)) == x for x in ages_seq)

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

from xoutil.future.codecs import safe_encode
from xotl.ql.core import thesefy

from .metamodel import (
    TransitiveRelationDescriptor,
    backref,
    date_property,
    age_property
)


@thesefy
class Entity:
    def __init__(self, **attrs):
        for attr, val in attrs.items():
            setattr(self, attr, val)

    def __repr__(self):
        from xoutil.names import nameof
        name = getattr(self, 'name', None)
        if name:
            return str("<%s '%s'>" % (
                nameof(type(self), inner=True, full=True),
                safe_encode(name)))
        else:
            return super().__repr__()


class Place(Entity):
    located_in = TransitiveRelationDescriptor('located_in')
    foundation_date = date_property('_foundation_date')
    age = age_property('foundation_date')


Place.located_in.target = Place


class Person(Entity):
    lives_in = TransitiveRelationDescriptor('located_in', Place)
    birthdate = date_property('_birthdate')
    age = age_property('birthdate')
    mother = backref('mother', 'children')
    father = backref('father', 'children')

    def __init__(self, **attrs):
        super().__init__(**attrs)
        self.children = []  # ensure all persons has this attr


Person.mother.target = Person
Person.father.target = Person

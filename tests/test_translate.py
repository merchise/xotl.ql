#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#----------------------------------------------------------------------
# xotl.ql.tests.test_translate
#----------------------------------------------------------------------
# Copyright (c) 2013 Merchise Autrement and Contributors
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under
# the terms of the LICENCE attached in the distribution package.
#
# Created on 2013-01-29

from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        unicode_literals as _py3_unicode,
                        absolute_import as _py3_abs_imports)

import unittest
import pytest

from xoutil.context import context
from xoutil.proxy import UNPROXIFING_CONTEXT
from xoutil.types import Unset
from xoutil.compat import iteritems_

from xotl.ql.core import these, this, thesefy
from xotl.ql.translation import init, token_before_filter


__docstring_format__ = 'rst'
__author__ = 'manu'


__LOG = False


if __LOG:
    import sys
    from xoutil.compat import iterkeys_
    from xoutil.aop.classical import weave, _weave_around_method

    from xotl.ql.tests import logging_aspect
    from xotl.ql.core import QueryParticlesBubble, _part_operations, QueryPart

    # Weave logging aspect into every relevant method during testing
    aspect = logging_aspect(sys.stdout)
    weave(aspect, QueryParticlesBubble)
    for attr in iterkeys_(_part_operations):
        _weave_around_method(QueryPart, aspect, attr, '_around_')
    _weave_around_method(QueryPart, aspect, '__getattribute__', '_around_')



# Initialize and configure the query translation components provided by the
# translate module. DON'T REMOVE since, some tests actually test this kind of
# facility. Also, DON'T put it the setUp of any test cases, cause it will
# likely fail.
init()


# The following classes are just a simple Object Model
class TransitiveRelationDescriptor(object):
    def __init__(self, name, target=None):
        self.name = name
        self.internal_name = '_' + name
        self.target = target

    def __get__(self, instance, cls):
        if instance is None:
            return self
        else:
            result = getattr(instance, self.internal_name, None)
            if result:
                queue = [result]
                result = [result]
                while queue:
                    current = queue.pop(0)
                    children = getattr(current, self.name, Unset)
                    queue.extend(child for child in children if child not in queue)
                    result.extend(child for child in children if child not in result)
            return result

    def __set__(self, instance, value):
        if value is None:
            delattr(instance, self.internal_name)
        else:
            assert self.target is None or isinstance(value, self.target)
            setattr(instance, self.internal_name, [value])


@thesefy
class Entity(object):
    def __init__(self, **attrs):
        for k, v in iteritems_(attrs):
            setattr(self, k, v)


def date_property(internal_attr_name):
    '''Creates a property date property that accepts string repr of dates

    :param internal_attr_name: The name of the attribute that will be used
                               internally to store the value. It should be
                               different that the name of the property itself.
    '''
    def getter(self):
        return getattr(self, internal_attr_name)

    def setter(self, value):
        from datetime import datetime
        if not isinstance(value, datetime):
            from re import compile
            pattern = compile(r'(\d{4})-(\d{1,2})-(\d{1,2})')
            match = pattern.match(value)
            if match:
                year, month, day = match.groups()
                value = datetime(year=int(year),
                                 month=int(month),
                                 day=int(day))
            else:
                raise ValueError('Invalid date')
        setattr(self, internal_attr_name, value)

    def fdel(self):
        delattr(self, internal_attr_name)

    return property(getter, setter, fdel)


def age_property(start_attr_name, end_attr_name=None):
    '''Creates a property for calculating the `age` given an
    attribute that holds the starting date of the event.

    :param start_attr_name: The name of the attribute that holds the
                            starting date of the event.
    :param end_attr_name: The name of the attribute that holds the end date
                          of the event. If None, each time `age` is calculated
                          `today` is used as the end date.
    :returns: The age in years (using 365.25 days per year).
    '''
    @property
    def age(self):
        from datetime import datetime
        end = datetime.today() if not end_attr_name else getattr(self,
                                                                 end_attr_name)
        date = getattr(self, start_attr_name)
        age = end - date
        return age.days // 365.25
    return age


class Place(Entity):
    located_in = TransitiveRelationDescriptor('located-in')
    foundation_date = date_property('_foundation_date')
    age = age_property('foundation_date')
Place.located_in.target = Place


class Person(Entity):
    lives_in = TransitiveRelationDescriptor('located-in', Place)
    birthdate = date_property('_birthdate')
    age = age_property('birthdate')


cuba = Place(name='Cuba', type='Country')
havana = Place(name='Havana', type='Province', located_in=cuba)
lisa = Place(name='La lisa', type='Municipality', located_in=havana)
cotorro = Place(name='Cotorro', type='Municipality', located_in=havana)
ciego = Place(name='Ciego de Ávila', type='Province', located_in=cuba)
moron = Place(name='Morón', type='Municipality', located_in=ciego)

elsa = Person(name='Elsa Acosta Cabrera',
              birthdate='1947-10-06',
              lives_in=moron)
manu = Person(name='Manuel Vázquez Acosta',
              birthdate='1978-10-21',
              mother=elsa,
              lives_in=lisa)

denia = Person(name='Ana Denia Pérez',
               birthdate='1950-04-01',
               lives_in=cotorro)
pedro = Person(name='Pedro Piñero', birthdate='1950-04-01', lives_in=cotorro)
yade = Person(name='Yadenis Piñero Pérez', birthdate='1979-05-16',
              mother=denia, father=pedro, lives_in=lisa)

manolito = Person(name='Manuel Vázquez Piñero',
                  birthdate='2007-03-22',
                  mother=yade,
                  father=manu,
                  lives_in=lisa)


# Three days after I (manu) wrote this query, I started to appear in the
# results ;)
def test_naive_plan_no_join(**kwargs):
    from xoutil.iterators import dict_update_new
    from xotl.ql.translation import naive_translation
    select_old_entities = these(who
                                for who in Entity
                                if who.name.startswith('Manuel'))
    dict_update_new(kwargs, dict(only='test_translate.*'))
    plan = naive_translation(select_old_entities, **kwargs)
    result = plan()
    assert (manu, ) in result
    assert (manolito, ) in result
    assert (yade, ) not in result


def test_ridiculous_join(**kwargs):
    from itertools import product
    from xoutil.iterators import dict_update_new
    from xotl.ql.translation import naive_translation
    select_old_entities = these((who, who2)
                                for who in Person
                                for who2 in Person)
    dict_update_new(kwargs, dict(only='test_translate.*'))
    plan = naive_translation(select_old_entities, **kwargs)
    result = list(plan())
    source = (elsa, manu, denia, pedro, yade, manolito)
    for pair in product(source, source):
        assert pair in result

class B(object):
    a = [1, 2]

class X(object):
    def __init__(self):
        self.b = B()

#@pytest.xfail()
def test_traversing_by_nonexistent_attribute(**kwargs):
    from xoutil.iterators import dict_update_new
    from xotl.ql.translation import naive_translation
    dict_update_new(kwargs, dict(only='test_translate.*'))

    # There's no `childs` attribute in Persons
    query = these(child for parent in Person
                        if parent.childs & (parent.age > 30)
                        for child in parent.childs
                        if child.age < 10)
    plan = naive_translation(query, **kwargs)
    assert list(plan()) == []

    # And much less a `foobar`
    query = these(parent for parent in Person if parent.foobar)
    plan = naive_translation(query, **kwargs)
    assert list(plan()) == []

    # And traversing through a non-existing stuff doesn't make
    # any sense either, but should not fail
    query = these(foos.name
                  for person in Person
                  for foos in person.foobars)
    plan = naive_translation(query, **kwargs)
    assert list(plan()) == []

    # However either trying to traverse to a second level without testing
    # should fail
    query = these(a for p in this for a in p.b.a)
    plan = naive_translation(query, **kwargs)
    with pytest.raises(AttributeError):
        list(plan())

    # The same query in a safe fashion
    query = these(a
                  for p in this
                  if p.b & p.b.a
                  for a in p.b.a)
    plan = naive_translation(query, **kwargs)
    assert list(plan()) == []


    # Now let's rerun the plan after we create some object that matches
    x = X()
    # Currently this is failing cause each result yielded from a query is
    # encoded in a tuple. Probably this is the expected behavior. Currently I
    # just allow it to fail to remind me that I must address this question.
    assert list(plan()) == x.b.a


class TestTranslatorTools(unittest.TestCase):
    def test_cotraverse_expression(self):
        from xoutil.compat import izip
        from xotl.ql.expressions import is_a
        from xotl.ql.translation import cotraverse_expression

        @thesefy
        class Person(object):
            pass

        @thesefy
        class Partnership(object):
            pass

        query = these((person, partner)
                      for person, partner in izip(Person, Person)
                      for rel in Partnership
                      if (rel.subject == person) & (rel.obj == partner))
        filters = list(query.filters)
        person, partner = query.selection
        person_is_a_person = is_a(person, Person)
        partner_is_a_person = is_a(partner, Person)
        with context(UNPROXIFING_CONTEXT):
            self.assertNotEqual(person, partner)
            self.assertIn(person_is_a_person, filters)
            self.assertIn(partner_is_a_person, filters)
            filters.remove(person_is_a_person)
            filters.remove(partner_is_a_person)
            # left filter are is_a(rel, Partnership) and the explicit we see in
            # the query expression
            self.assertIs(2, len(filters))

            rel_is_a = next(f for f in filters
                            if f.operation == is_a)
            filters.remove(rel_is_a)

            # there are 4 named instances in the left filter
            # (rel.subject == person) & (rel.obj == partner)
            self.assertIs(4, len(list(cotraverse_expression(filters[0]))))


class TestOrderingExpressions(unittest.TestCase):
    def test_token_before_filter(self):
        query = these((parent, child)
                      for parent in this
                      if parent.children
                      for child in parent.children
                      if child.age < 5
                      for dummy in parent.children)


        parent, child = query.selection
        parent_token, children_token, dummy_token = query.tokens
        expr1, expr2 = query.filters

        def ok(e1, e2):
            with context(UNPROXIFING_CONTEXT):
                assert e1 == e2
        ok(expr1, parent.children)
        ok(expr2, child.age < 5)

        assert not token_before_filter(children_token, expr1), repr((children_token, expr1, expr2))
        assert token_before_filter(children_token, expr2, True)
        assert token_before_filter(parent_token, expr2, True)
        assert not token_before_filter(dummy_token, expr2, True)


def test_regression_test_token_before_filter_20130401():
    '''
    '''
    query = these(who
                  for who in Entity
                  if who.name.starswith('Manuel'))
    is_entity_filter, name_filter = query.filters
    token = query.tokens[0]
    assert len(query.tokens) == 1
    assert token_before_filter(token, is_entity_filter, True)
    assert token_before_filter(token, name_filter, True)


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main(verbosity=2)

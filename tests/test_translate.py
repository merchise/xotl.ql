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
try:
    import pytest
except:
    class pytest(object):
        class _mark(object):
            def __getattr__(self, attr):
                return lambda *a, **kw: (lambda f: f)
        mark = _mark()

from xoutil.context import context
from xoutil.proxy import UNPROXIFING_CONTEXT
from xoutil.types import Unset
from xoutil.compat import iteritems_

from xotl.ql.core import these, this, thesefy
from xotl.ql.translation import token_before_filter

from xotl.ql.translation.py import init


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


class backref(object):
    def __init__(self, name, ref):
        self.name = name
        self._name = 'backref_%s' % name
        self.ref = ref

    def __get__(self, inst, cls):
        if not inst:
            return self
        else:
            return getattr(inst, self._name, None)

    def __set__(self, inst, value):
        from xoutil.objects import setdefaultattr
        target = getattr(self, 'target', None)
        if target and not isinstance(value, target):
            raise TypeError('Cannot assign %s to %s' % (value, self.name))
        previous = getattr(inst, self._name, None)
        if previous:
            backrefs = getattr(previous, self.ref)
            backrefs.remove(self)
        setattr(inst, self._name, value)
        backrefs = setdefaultattr(value, self.ref, [])
        backrefs.append(inst)

@thesefy
class Entity(object):
    def __new__(cls, **attrs):
        from xoutil.objects import setdefaultattr
        this_instances = setdefaultattr(Entity, 'this_instances', [])
        res = super(Entity, cls).__new__(cls, **attrs)
        this_instances.append(res)
        return res

    def __init__(self, **attrs):
        for k, v in iteritems_(attrs):
            setattr(self, k, v)

    def __repr__(self):
        from xoutil.names import nameof
        name = getattr(self, 'name', None)
        if name:
            return str("<%s '%s'>" % (nameof(type(self), inner=True, full=True), name.encode('ascii', 'replace')))
        else:
            return super(Entity, self).__repr__()


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


# So that ages are stable in tests
def get_birth_date(age, today=None):
    from datetime import datetime, timedelta
    if today is None:
        today = datetime.today()
    birth = today - timedelta(days=age*365)
    # Brute force
    if get_age(birth, today) == age:
        return birth
    while get_age(birth, today) < age:
        birth += timedelta(days=1)
    while get_age(birth, today) > age:
        birth -= timedelta(days=1)
    return birth


def get_age(birthdate, today=None):
    from datetime import datetime
    if today is None:
        today = datetime.today()
    age = today - birthdate
    return age.days / 365


def test_ages():
    import random
    ages = range(4, 80)
    ages_seq = (random.choice(ages) for _ in range(100))
    assert all(get_age(get_birth_date(x)) == x for x in ages_seq)


def age_property(start_attr_name, end_attr_name=None, age_attr_name=None):
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
        return get_age(date, end)
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
    mother = backref('mother', 'children')
    father = backref('father', 'children')
Person.mother.target = Person
Person.father.target = Person


cuba = Place(name='Cuba', type='Country')
havana = Place(name='Havana', type='Province', located_in=cuba)
lisa = Place(name='La lisa', type='Municipality', located_in=havana)
cotorro = Place(name='Cotorro', type='Municipality', located_in=havana)
ciego = Place(name='Ciego de Ávila', type='Province', located_in=cuba)
moron = Place(name='Morón', type='Municipality', located_in=ciego)

assert len(Place.this_instances) == 6


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


# In PyPy::
#    Python 2.7.2 (1.9+dfsg-1, Jun 19 2012, 23:45:31)
#    [PyPy 1.9.0 with GCC 4.7.0] on linux2)
#
# For some reason (currenly unknown) under PyPy the following tests fail. The
# core of the problem resides in that context[UNPROXIFING_CONTEXT] is
# considered True in places where no `with` is around. Maybe is a bug PyPy, I
# can't be sure.
#
# You should notice that the translation.py module is NOT considered to be
# a production module, but a proof of concept for translation from xotl.ql
# as a language.
#

@pytest.mark.xfail(str("sys.version.find('PyPy') != -1"))
def test_all_pred(**kwargs):
    from xoutil.iterators import dict_update_new
    from xotl.ql.expressions import all_, sum_
    from xotl.ql.translation.py import naive_translation
    query = these(parent
                  for parent in Person
                  if parent.children
                  if all_((30 < child.age) & (child.age < 36) for child in parent.children))
    dict_update_new(kwargs, dict(only='test_translate.*'))
    plan = naive_translation(query, **kwargs)
    result = list(plan())
    assert elsa in result
    assert papi in result
    assert len(result) == 2

    query = these(parent
                  for parent in Person
                  if parent.children
                  if all_(parent.name.startswith('Manu'), parent.age > 30))

    dict_update_new(kwargs, dict(only='test_translate.*'))
    plan = naive_translation(query, **kwargs)
    with pytest.raises(SyntaxError):
        result = list(plan())


    query = these(parent
                  for parent in Person
                  if parent.children
                  if sum_(child.age for child in parent.children) > 60)

    dict_update_new(kwargs, dict(only='test_translate.*'))
    plan = naive_translation(query, **kwargs)
    result = list(plan())
    assert denia in result
    assert pedro in result
    assert len(result) == 2


@pytest.mark.xfail(str("sys.version.find('PyPy') != -1"))
def test_naive_plan_no_join(**kwargs):
    from xoutil.iterators import dict_update_new
    from xotl.ql.translation.py import naive_translation
    select_old_entities = these(who
                                for who in Entity
                                if who.name.startswith('Manuel'))
    dict_update_new(kwargs, dict(only='test_translate.*'))
    plan = naive_translation(select_old_entities, **kwargs)
    result = list(plan())
    assert manu in result
    assert manolito in result
    assert yade not in result


@pytest.mark.xfail(str("sys.version.find('PyPy') != -1"))
def test_ridiculous_join(**kwargs):
    from itertools import product
    from xoutil.iterators import dict_update_new
    from xotl.ql.translation.py import naive_translation
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

@pytest.mark.xfail(str("sys.version.find('PyPy') != -1"))
def test_traversing_by_nonexistent_attribute(**kwargs):
    from xoutil.iterators import dict_update_new
    from xotl.ql.translation.py import naive_translation
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
    assert list(plan()) == x.b.a

@pytest.mark.xfail(str("sys.version.find('PyPy') != -1"))
def test_token_before_filter():
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

    assert UNPROXIFING_CONTEXT not in context
    assert not token_before_filter(children_token, expr1), repr((children_token, expr1, expr2))
    assert token_before_filter(children_token, expr2, True)
    assert token_before_filter(parent_token, expr2, True)
    assert not token_before_filter(dummy_token, expr2, True)
    assert UNPROXIFING_CONTEXT not in context


@pytest.mark.xfail(str("sys.version.find('PyPy') != -1"))
def test_regression_test_token_before_filter_20130401():
    assert UNPROXIFING_CONTEXT not in context
    query = these(who
                  for who in Entity
                  if who.name.starswith('Manuel'))
    is_entity_filter, name_filter = query.filters
    token = query.tokens[0]
    assert len(query.tokens) == 1
    assert token_before_filter(token, is_entity_filter, True)
    assert token_before_filter(token, name_filter, True)


@pytest.mark.xfail(str("sys.version.find('PyPy') != -1"))
def test_translation_with_partition():
    from xoutil.iterators import zip
    from xotl.ql.expressions import call
    from xotl.ql.translation.py import naive_translation

    @thesefy
    class Universe(int):
        pass
    Universe.this_instances = [Universe(i) for i in range(2, 10)]

    def gcd(a, b):
        while a % b != 0:
            a, b = b, a % b
        return b

    expected = set((a, b) for a in range(2, 10) for b in range(2, 10) if a > b and gcd(a, b) == 1)
    assert expected == set([(3, 2),
                            (4, 3),
                            (5, 2), (5, 3), (5, 4),
                            (6, 5),
                            (7, 2), (7, 3), (7, 4), (7, 5), (7, 6),
                            (8, 3), (8, 5), (8, 7),
                            (9, 2), (9, 4), (9, 5), (9, 7), (9, 8)])

    query = these((a, b) for a, b in zip(Universe, Universe) if (a > b) & (call(gcd, a, b) == 1))
    plan = naive_translation(query)
    assert set(plan()) == set([(3, 2),
                               (4, 3),
                               (5, 2), (5, 3), (5, 4),
                               (6, 5),
                               (7, 2), (7, 3), (7, 4), (7, 5), (7, 6),
                               (8, 3), (8, 5), (8, 7),
                               (9, 2), (9, 4), (9, 5), (9, 7), (9, 8)])


    query = these(((a, b) for a, b in zip(Universe, Universe) if (a > b) & (call(gcd, a, b) == 1)), offset=100)
    plan = naive_translation(query)
    assert len(list(plan())) == 0

def test_ordering():
    from xotl.ql.translation.py import naive_translation

    @thesefy
    class Universe(int):
        pass
    Universe.this_instances = [Universe(i) for i in range(2, 10)]

    query = these((which for which in Universe),
                   ordering=lambda which: -which)
    plan = naive_translation(query)
    assert list(plan()) == list(reversed(range(2, 10)))

    query = these((which for which in Universe),
                   ordering=lambda which: +which)
    plan = naive_translation(query)
    assert list(plan()) == list(range(2, 10))  #XXX: Py3k list()

    query = these((person for person in Person),
                  ordering=lambda person: -person.age)
    plan = naive_translation(query)
    results = list(plan())
    assert manolito == results[-1]
    assert elsa == results[0]

    query = these((person for person in Person if person.children))
    plan = naive_translation(query)
    results = list(plan())
    parents = (manu, yade, pedro, papi, elsa, ppp, denia)
    for who in parents:
        assert who in results
    assert len(results) == len(parents)

    from xotl.ql.expressions import sum_
    query = these((person for person in Person if person.children),
                  ordering=lambda person: (-sum_(child.age for child in person.children), -person.age))
    plan = naive_translation(query)
    results = list(plan())
    assert pedro == results[0]


def test_short_circuit():
    from xotl.ql import thesefy
    from xotl.ql.expressions import call
    from xotl.ql.translation.py import naive_translation
    from xoutil.compat import integer
    flag = [0]   # A list to allow non-global non-local in Py2k
    def inc_flag(by=1):
        flag[0] += 1
        return flag[0]

    @thesefy
    class Universe(integer):
        pass
    Universe.this_instances = [Universe(1780917517912941696167)]

    query = these(atom for atom in Universe if (call(inc_flag) > 1) & call(inc_flag))
    plan = naive_translation(query)
    list(plan())
    assert flag[0] == 1

    flag[0] = 0
    query = these(atom for atom in Universe if (call(inc_flag) > 0) | call(inc_flag))
    plan = naive_translation(query)
    list(plan())
    assert flag[0] == 1

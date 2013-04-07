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
        backrefs.append(self)

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


# So that ages are stable in tests
def get_birth_date(age):
    from datetime import datetime, timedelta
    today = datetime.today()
    birth = today - timedelta(days=age*365.25)
    return birth

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
# ... the skipped tests take a long long time to do.
#
# You should notice that the translation.py module is NOT considered to be
# a production module, but a proof of concept for translation from xotl.ql
# as a language.
#
# The long time is due mostly to the fact even a simple script::
#
#   $ pypy -c "import gc; print len(gc.get_objects())"
#   21434
#
# shows that there are LOTS of objects created in the first place, while in
# Python 2.7 and 3.2 this figure is much smaller (although still high)::
#
#   $ python3 -c "import gc; print(len(gc.get_objects()))"
#   5136
#
#   $ python -c "import gc; print len(gc.get_objects())"
#   3564
#
#
# For the sake of testability I skip those tests in PyPy. Still the core of
# xotl.ql is almost working in PyPy.


@pytest.mark.xfail()  # all_ not implemented ok.
@pytest.mark.skipif(str("sys.version.find('PyPy') != -1"))
def test_all_pred():
    from xotl.ql.expressions import all_
    from xotl.ql.translation.py import naive_translation
    query = these(parent
                  for parent in Person
                  if parent.children
                  if all_((30 < child.age) & (child.age < 35) for child in parent.children))
    plan = naive_translation(query)
    result = list(plan())
    assert elsa in result
    assert papi in result
    assert len(result) == 2


@pytest.mark.skipif(str("sys.version.find('PyPy') != -1"))
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


@pytest.mark.skipif(str("sys.version.find('PyPy') != -1"))
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

@pytest.mark.skipif(str("sys.version.find('PyPy') != -1"))
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
    # Currently this is failing cause each result yielded from a query is
    # encoded in a tuple. Probably this is the expected behavior. Currently I
    # just allow it to fail to remind me that I must address this question.
    assert list(plan()) == x.b.a


# For some reason (currenly unknown) under PyPy the following tests fail. The
# core of the problem resides in that context[UNPROXIFING_CONTEXT] is
# considered True in places where no with is around. Maybe is a bug PyPy, I
# can't be sure.

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


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main(verbosity=2)

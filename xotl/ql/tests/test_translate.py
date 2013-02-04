#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#----------------------------------------------------------------------
# xotl.ql.tests.test_translate
#----------------------------------------------------------------------
# Copyright (c) 2012 Merchise Autrement
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License (GPL) as published by the Free
# Software Foundation;  either version 2  of  the  License, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Created on Jul 2, 2012


from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        unicode_literals as _py3_unicode,
                        absolute_import as _absolute_import)


import unittest

from xoutil.context import context
from xoutil.proxy import UNPROXIFING_CONTEXT
from xoutil.types import Unset

from xotl.ql.core import these, this, thesefy
from xotl.ql.translate import init


__docstring_format__ = 'rst'
__author__ = 'manu'


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

    def __get__(self, instance, cls):
        if instance is None:
            return self
        else:
            result = getattr(instance, self.internal_name, [])
            if result:
                current = result
                while current:
                    current = getattr(current, self.name, Unset)
                    if current and current not in result:
                        result.append(current)
            return result

    def __set__(self, instance, value):
        setattr(instance, self.internal_name, value)


@thesefy
class Entity(object):
    def __init__(self, **attrs):
        for k, v in attrs.iteritems():
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
            import dateutil.parser
            value = dateutil.parser.parse(value)
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


select_manus = these(who for who in Person if who.name.startswith('Manuel '))
select_aged_entities = these(who for who in Entity if who.age)

# Three days after I (manu) wrote this query, I started to appear in the
# results ;)
select_old_entities = these(who for who in Entity if who.age > 34)



class TestTranslatorTools(unittest.TestCase):
    def test_cofind_tokens(self):
        from itertools import izip
        from xotl.ql.expressions import is_a
        from xotl.ql.translate import cofind_tokens

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
            self.assertIs(4, len(list(cofind_tokens(filters[0]))))



if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main(verbosity=2)

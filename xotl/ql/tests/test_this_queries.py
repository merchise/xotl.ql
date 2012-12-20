#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#----------------------------------------------------------------------
# xotl.ql.tests.test_this_queries
#----------------------------------------------------------------------
# Copyright (c) 2012 Merchise Autrement
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License (GPL) as published by the
# Free Software Foundation;  either version 2  of  the  License, or (at
# your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA 02110-1301, USA.
#
# Created on Jun 15, 2012

from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        unicode_literals as _py3_unicode,
                        absolute_import as _py3_abs_import)

import unittest

from xoutil.context import context
from xoutil.proxy import UNPROXIFING_CONTEXT, unboxed

from xotl.ql import this
from xotl.ql.core import these, provides_any
from xotl.ql.interfaces import IQueryObject
from xotl.ql.core import QueryParticlesBubble, QueryPart, _part_operations


from zope.interface import implementer

__docstring_format__ = 'rst'
__author__ = 'manu'


__LOG = False


if __LOG:
    import sys
    from itertools import chain
    from xoutil.compat import iterkeys_
    from xoutil.aop.classical import weave, _weave_around_method

    from xotl.ql.tests import logging_aspect

    # Weave logging aspect into every relevant method during testing
    aspect = logging_aspect(sys.stdout)
    weave(aspect, QueryParticlesBubble)
    for attr in iterkeys_(_part_operations):
        _weave_around_method(QueryPart, aspect, attr, '_around_')
    _weave_around_method(QueryPart, aspect, '__getattribute__', '_around_')


class TestUtilities(unittest.TestCase):
    def _test_class(self, Person):
        from xotl.ql.expressions import is_instance

        q = these((who for who in Person if who.age > 30),
                  limit=100)
        # We assume that Person has been thesefied with thesefy('Person')
        who = domain = this('Person')
        q1 = these(w for w in domain if is_instance(w, Person)
                        if w.age > 30)

        is_filter = is_instance(who, Person)
        age_filter = who.age > 30
        with context(UNPROXIFING_CONTEXT):
            self.assertEqual(2, len(q.filters))
            self.assertEqual(2, len(q1.filters))
            self.assertIn(is_filter, q.filters)
            self.assertIn(is_filter, q1.filters)
            self.assertIn(age_filter, q.filters)
            self.assertIn(age_filter, q1.filters)

            self.assertEqual(q.selection, q1.selection)
            self.assertEqual(q.tokens, q1.tokens)

    def test_thesefy_good(self):
        from xotl.ql.core import thesefy

        @thesefy("Person")
        class Person(object):
            pass
        self._test_class(Person)

    def test_thesefy_meta_no_iter(self):
        from xotl.ql.core import thesefy

        class Meta(type):
            pass

        @thesefy("Person")
        class Person(object):
            __metaclass__ = Meta
        self._test_class(Person)

    def test_thesefy_good_meta(self):
        from xotl.ql.core import thesefy

        class Meta(type):
            def __iter__(self):
                from xoutil.objects import nameof
                return iter(this(nameof(self)))

        @thesefy("Person")
        class Person(object):
            __metaclass__ = Meta

        q = these(who for who in Person if who.age > 30)
        q1 = these(who for who in this('Person') if who.age > 30)
        with context(UNPROXIFING_CONTEXT):
            self.assertEqual(q.selection, q1.selection)

    def test_thesefy_doesnot_messup_identities(self):
        from itertools import izip
        from xotl.ql.core import thesefy
        from xotl.ql.expressions import is_a

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


class TestThisQueries(unittest.TestCase):
    def setUp(self):
        from xotl.ql.core import QueryParticlesBubble
        setattr(QueryParticlesBubble, '__repr__', lambda self: hex(id(self)))

    def test_most_basic_query(self):
        query = these(parent for parent in this('parent') if parent.age > 40)
        self.assertTrue(provides_any(query, IQueryObject))
        (p, ) = query.selection
        token_expectation = p_expected = this('parent')
        filter_expectation = this('parent').age > 40

        with context(UNPROXIFING_CONTEXT):
            self.assertEqual(p, p_expected)

            filters = query.filters
            self.assertEqual(1, len(filters))
            self.assertIn(filter_expectation, filters)

            tokens = query.tokens
            self.assertEqual(1, len(tokens))
            self.assertIn(token_expectation, tuple(tokens))

    def test_basic_queries(self):
        from xotl.ql.expressions import count
        query = these((parent.title + parent.name, count(child.toys))
                        for parent in this('parent')
                        if parent.age < 40
                        for child in parent.children
                        if child.age > 5)
        self.assertTrue(provides_any(query, IQueryObject))

        (parent_full_name, child_toys) = query.selection
        full_name_expectation = this('parent').title + this('parent').name
#        child_name_expectation = this('parent').children.name
        child_toys_expectation = count(this('parent').children.toys)

        parent_age_test = this('parent').age < 40
        children_age_test = this('parent').children.age > 5

        parent_token = this('parent')
        children_token = this('parent').children

        with context(UNPROXIFING_CONTEXT):
            self.assertEqual(parent_full_name, full_name_expectation)
#            self.assertEqual(child_name, child_name_expectation)
            self.assertEqual(child_toys, child_toys_expectation)

            filters = query.filters
            self.assertEqual(2, len(filters))
            self.assertIn(parent_age_test, filters)
            self.assertIn(children_age_test, filters)

            tokens = query.tokens
            self.assertEqual(2, len(tokens))
            self.assertIn(parent_token, tokens)
            self.assertIn(children_token, tokens)

    def test_complex_query_with_3_tokens(self):
        query = these((parent.title + parent.name,
                       child.name + child.nick, toy.name)
                      for parent in this('parent')
                      if parent.children
                      for child in parent.children
                      if child.toys
                      for toy in child.toys
                      if (parent.age > 32) & (child.age < 5) |
                         (toy.type == 'laptop'))
        p = this('parent')
        c = p.children
        t = c.toys

        filters = query.filters
        expected_filters = [((p.age > 32) & (c.age < 5) | (t.type == 'laptop')),
                            p.children, c.toys]

        tokens = query.tokens
        expected_tokens = [p, c, t]

        selection = query.selection
        expected_selection = (p.title + p.name, c.name + c.nick, t.name)
        with context(UNPROXIFING_CONTEXT):
            self.assertEqual(selection, expected_selection)

            self.assertEqual(len(expected_filters), len(filters))
            for f in expected_filters:
                self.assertIn(f, filters)

            self.assertEqual(len(expected_tokens), len(tokens))
            for t in expected_tokens:
                self.assertIn(t, tokens)


from xotl.ql.expressions import OperatorType, UNARY, BINARY, N_ARITY
_tests = {}


def _build_unary_test(op):
    def test(self):
        operator = getattr(op, '_python_operator', op)
        query = these(parent for parent in this('p') if operator(parent.age))
        expected = operator(this('p').age)
        self.assertIs(1, len(query.filters))
        with context(UNPROXIFING_CONTEXT):
            self.assertEqual(expected, query.filters[0])
    test.__name__ = b'test_for_{0}'.format(op.__name__)
    return test


def _build_binary_test(op):
    def test(self):
        operator = getattr(op, '_python_operator', op)
        query = these(parent for parent in this('p') if operator(parent.age, parent.check))
        expected = operator(this('p').age, this('p').check)
        self.assertIs(1, len(query.filters))
        with context(UNPROXIFING_CONTEXT):
            self.assertEqual(expected, query.filters[0])
    test.__name__ = b'test_for_{0}'.format(op.__name__)
    return test


def _build_nary_test(op):
    def test(self):
        operator = getattr(op, '_python_operator', op)
        query = these(parent for parent in this('p') if operator(parent.age, parent.check, parent.names))
        expected = operator(this('p').age, this('p').check, this('p').names)
        self.assertIs(1, len(query.filters))
        with context(UNPROXIFING_CONTEXT):
            self.assertEqual(expected, query.filters[0])
    test.__name__ = b'test_for_{0}'.format(op.__name__)
    return test


for op in OperatorType.operators:
    if getattr(op, 'arity', None) is UNARY:
        _tests['test_for_{0}'.format(op.__name__)] = _build_unary_test(op)
    elif getattr(op, 'arity', None) is BINARY:
        _tests['test_for_{0}'.format(op.__name__)] = _build_binary_test(op)
    elif getattr(op, 'arity', None) is N_ARITY:
        _tests['test_for_{0}'.format(op.__name__)] = _build_nary_test(op)

TestAllOperations = type(b'TestAllOperations', (unittest.TestCase, ), _tests)


class Regression20121030_ForgottenTokensAndFilters(unittest.TestCase):
    '''
    Non-selected tokens should not be forgotten.

    This tests copycats most of the test_thesey_doesnot_messup_identities
    There's was two related bugs there:
       - There should be a token for rel
       - There should be a filter `is_instance(rel, Partnetship)`

    '''
    def test_is_a_partnership_is_not_forgotten(self):
        from itertools import izip
        query = these((person, partner)
                      for person, partner in izip(this('person'),
                                                  this('partner'))
                      for rel in this('relation')
                      if rel.type == 'partnership'
                      if (rel.subject == person) & (rel.object == partner))
        filters = list(query.filters)
        expected_rel_type = this('relation').type == 'partnership'
        with context(UNPROXIFING_CONTEXT):
            self.assertIn(expected_rel_type, filters)
            self.assertIs(2, len(filters))

    def test_theres_a_token_for_partnership(self):
        from itertools import izip
        query = these((person, partner)
                      for person, partner in izip(this('person'),
                                                  this('partner'))
                      for rel in this('relation')
                      if rel.type == 'partnership'
                      if (rel.subject == person) & (rel.object == partner))
        tokens = list(query.tokens)
        person, partner, rel = this('person'), this('partner'), this('relation')
        with context(UNPROXIFING_CONTEXT):
            self.assertIs(3, len(tokens))
            self.assertIn(rel, tokens)
            self.assertIn(person, tokens)
            self.assertIn(partner, tokens)

    def test_worst_case_must_have_3_filters_and_3_tokens(self):
        from itertools import izip
        query = these(person
                      for person, partner in izip(this('person'),
                                                  this('partner'))
                      for rel in this('relation')
                      if rel.type == 'partnership'
                      if rel.subject == person
                      if rel.object == partner
                      if partner.age > 32)
        filters = list(query.filters)
        tokens = list(query.tokens)
        person, partner, rel = this('person'), this('partner'), this('relation')
        expected_rel_type_filter = rel.type == 'partnership'
        expected_rel_subject_filter = rel.subject == person
        expected_rel_obj_filter = rel.object == partner
        expected_partner_age = partner.age > 32
        with context(UNPROXIFING_CONTEXT):
            self.assertIs(4, len(filters))
            self.assertIn(expected_rel_type_filter, filters)
            self.assertIn(expected_rel_subject_filter, filters)
            self.assertIn(expected_rel_obj_filter, filters)
            self.assertIn(expected_partner_age, filters)

            self.assertIn(person, tokens)
            self.assertIn(rel, tokens)
            self.assertIs(3, len(tokens))
            self.assertIn(partner, tokens)


class RegressionTests(unittest.TestCase):
    def test_20121127_unnamed_this_leaked(self):
        query = these(parent for parent in this if parent.age > 30)
        term = query.filters[0].children[0]
        with context(UNPROXIFING_CONTEXT):
            self.assertEqual(unboxed(term).parent, query.tokens[0])

    def test_named_terms_matches_a_token(self):
        '''
        Ensures that all terms are named, and they are bound to a token that is
        in the query.
        '''
        from itertools import izip
        from xotl.ql.core import thesefy
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
                      if (rel.subject == person) & (rel.obj == partner)
                      if person.age > 35)

        tokens = query.tokens
        matches_token = lambda term: (term.name and (
                                      term.binding.expression in tokens or
                                      matches_token(term.parent)))
        with context(UNPROXIFING_CONTEXT):
            self.assertTrue(all(matches_token(term)
                                for term in cofind_tokens(*query.filters)))

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main(verbosity=2)

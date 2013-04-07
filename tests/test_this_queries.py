#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#----------------------------------------------------------------------
# xotl.ql.tests.test_this_queries
#----------------------------------------------------------------------
# Copyright (c) 2012, 2013 Merchise Autrement
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under
# the terms of the LICENCE attached in the distribution package.
#
# Created on Jun 15, 2012

from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        unicode_literals as _py3_unicode,
                        absolute_import as _py3_abs_import)

import unittest
import sys

from xoutil.context import context
from xoutil.proxy import UNPROXIFING_CONTEXT, unboxed

from xotl.ql import this
from xotl.ql.core import these, provides_any
from xotl.ql.interfaces import IQueryObject

__docstring_format__ = 'rst'
__author__ = 'manu'


def test_thesefy_when_inherited_uses_the_right_name():
    from xotl.ql.core import thesefy

    class Base(object):
        pass

    @thesefy
    class Entity(Base):
        pass

    class Person(Entity):
        pass

    assert Person.__name__ == 'Person'


class TestUtilities(unittest.TestCase):
    def _test_class(self, Person):
        from xotl.ql.expressions import is_instance

        q = these((who for who in Person if who.age > 30),
                  limit=100)
        # We assume that Person has been thesefied with thesefy('Person')
        who = domain = this('Person')
        q1 = these(w for w in domain
                   if is_instance(w, Person)
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
        from xoutil.iterators import izip
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


def test_most_basic_query():
    query = these(parent for parent in this('parent') if parent.age > 40)
    assert provides_any(query, IQueryObject)
    # Since the query selects a single object, a single object must be
    # placed as the selection (not a tuple!).
    p = query.selection
    token_expectation = p_expected = this('parent')
    filter_expectation = this('parent').age > 40

    with context(UNPROXIFING_CONTEXT):
        assert p == p_expected

        filters = query.filters
        assert len(filters) == 1
        assert filter_expectation in filters

        tokens = [tk.expression for tk in query.tokens]
        assert len(tokens) == 1
        assert token_expectation in tuple(tokens)

def test_basic_queries():
    from xotl.ql.expressions import count
    query = these((parent.title + parent.name, count(child.toys))
                    for parent in this('parent')
                    if parent.age < 40
                    for child in parent.children
                    if child.age > 5)
    assert provides_any(query, IQueryObject)

    (parent_full_name, child_toys) = query.selection
    full_name_expectation = this('parent').title + this('parent').name
    child_toys_expectation = count(this('parent').children.toys)

    parent_age_test = this('parent').age < 40
    children_age_test = this('parent').children.age > 5

    parent_token = this('parent')
    children_token = this('parent').children

    with context(UNPROXIFING_CONTEXT):
        assert parent_full_name == full_name_expectation
        assert child_toys == child_toys_expectation

        filters = query.filters
        assert len(filters) == 2
        assert parent_age_test in filters
        assert children_age_test in filters

        tokens = [tk.expression for tk in query.tokens]
        assert len(tokens) == 2
        assert parent_token in tokens
        assert children_token in tokens


def test_complex_query_with_3_tokens():
    query = these((parent.title + parent.name,
                   child.name + child.nick, toy.name)
                  for parent in this('parent')
                  if parent.children
                  for child in parent.children
                  if child.toys
                  for toy in child.toys
                  if (parent.age > 32) & (child.age < 5) | (toy.type == 'laptop'))
    p = this('parent')
    c = p.children
    t = c.toys

    filters = query.filters
    expected_filters = [((p.age > 32) & (c.age < 5) | (t.type == 'laptop')),
                        p.children, c.toys]

    tokens = [tk.expression for tk in query.tokens]
    expected_tokens = [p, c, t]

    selection = query.selection
    expected_selection = (p.title + p.name, c.name + c.nick, t.name)
    with context(UNPROXIFING_CONTEXT):
        assert selection == expected_selection

        assert len(expected_filters) == len(filters)
        for f in expected_filters:
            assert f in filters

        assert len(expected_tokens) == len(tokens)
        for t in expected_tokens:
            assert t in tokens


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
    test.__name__ = str('test_for_{0}'.format(op.__name__))
    return test


def _build_binary_test(op):
    def test(self):
        operator = getattr(op, '_python_operator', op)
        query = these(parent for parent in this('p') if operator(parent.age, parent.check))
        expected = operator(this('p').age, this('p').check)
        self.assertIs(1, len(query.filters))
        with context(UNPROXIFING_CONTEXT):
            self.assertEqual(expected, query.filters[0])
    test.__name__ = str('test_for_{0}'.format(op.__name__))
    return test


def _build_nary_test(op):
    def test(self):
        operator = getattr(op, '_python_operator', op)
        query = these(parent for parent in this('p') if operator(parent.age, parent.check, parent.names))
        expected = operator(this('p').age, this('p').check, this('p').names)
        self.assertIs(1, len(query.filters))
        with context(UNPROXIFING_CONTEXT):
            self.assertEqual(expected, query.filters[0])
    test.__name__ = str('test_for_{0}'.format(op.__name__))
    return test


for op in OperatorType.operators:
    if getattr(op, 'arity', None) is UNARY:
        _tests['test_for_{0}'.format(op.__name__)] = _build_unary_test(op)
    elif getattr(op, 'arity', None) is BINARY:
        _tests['test_for_{0}'.format(op.__name__)] = _build_binary_test(op)
    elif getattr(op, 'arity', None) is N_ARITY:
        _tests['test_for_{0}'.format(op.__name__)] = _build_nary_test(op)

AllOperationsBase = type(str('AllOperationsBase'), (object, ),
                         _tests)

class TestAllOperations(unittest.TestCase, AllOperationsBase):
    pass


def test_for_generator_as_sole_argument():
    from xotl.ql.core import QueryObject
    from xotl.ql.expressions import all_
    query = these(parent for parent in this
                  if all_(child.age < 5 for child in parent.children)
                  if all_(parent.children, this.age < 5)
                  if all_(this.children, this.age < 5))
    assert len(query.filters) == 3
    assert isinstance(query.filters[0].children[0], QueryObject)


# Non-selected tokens should not be forgotten.

# This tests copycats most of the test_thesey_doesnot_messup_identities
# There's was two related bugs there:
#    - There should be a token for rel
#    - There should be a filter `is_instance(rel, Partnetship)`

def test_is_a_partnership_is_not_forgotten():
    from xoutil.iterators import izip
    query = these((person, partner)
                  for person, partner in izip(this('person'),
                                              this('partner'))
                  for rel in this('relation')
                  if rel.type == 'partnership'
                  if (rel.subject == person) & (rel.object == partner))
    filters = list(query.filters)
    expected_rel_type = this('relation').type == 'partnership'
    with context(UNPROXIFING_CONTEXT):
        assert expected_rel_type in filters
        assert len(filters) == 2

def test_theres_a_token_for_partnership():
    from xoutil.iterators import izip
    query = these((person, partner)
                  for person, partner in izip(this('person'),
                                              this('partner'))
                  for rel in this('relation')
                  if rel.type == 'partnership'
                  if (rel.subject == person) & (rel.object == partner))
    tokens = [tk.expression for tk in query.tokens]
    person, partner, rel = this('person'), this('partner'), this('relation')
    with context(UNPROXIFING_CONTEXT):
        assert len(tokens) == 3
        assert rel in tokens
        assert person in tokens
        assert partner in tokens

def test_worst_case_must_have_3_filters_and_3_tokens():
    from xoutil.iterators import izip
    query = these(person
                  for person, partner in izip(this('person'),
                                              this('partner'))
                  for rel in this('relation')
                  if rel.type == 'partnership'
                  if rel.subject == person
                  if rel.object == partner
                  if partner.age > 32)
    filters = list(query.filters)
    tokens = [tk.expression for tk in query.tokens]
    person, partner, rel = this('person'), this('partner'), this('relation')
    expected_rel_type_filter = rel.type == 'partnership'
    expected_rel_subject_filter = rel.subject == person
    expected_rel_obj_filter = rel.object == partner
    expected_partner_age = partner.age > 32
    with context(UNPROXIFING_CONTEXT):
        assert len(filters) == 4
        assert expected_rel_type_filter in filters
        assert expected_rel_subject_filter in filters
        assert expected_rel_obj_filter in filters
        assert expected_partner_age in filters

        assert len(tokens) == 3
        assert person in tokens
        assert rel in tokens
        assert partner in tokens


def test_20121127_unnamed_this_leaked():
    query = these(parent for parent in this if parent.age > 30)
    term = query.filters[0].children[0]
    with context(UNPROXIFING_CONTEXT):
        assert unboxed(term).parent == query.tokens[0].expression

def test_named_terms_matches_a_token():
    '''
    Ensures that all terms are named, and they are bound to a token that is
    in the query.
    '''
    from xoutil.iterators import izip
    from xotl.ql.core import thesefy
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
                  if (rel.subject == person) & (rel.obj == partner)
                  if person.age > 35)

    tokens = [tk.expression for tk in query.tokens]
    matches_token = lambda term: (term.name and (
                                  term.binding.expression in tokens or
                                  matches_token(term.parent)))
    with context(UNPROXIFING_CONTEXT):
        assert all(matches_token(term)
                   for term in cotraverse_expression(*query.filters))


def test_loosing_tokens():
    query = these((child, brother)
                  for parent in this
                  for child in parent.children
                  for brother in parent.children
                  if child is not brother)
    assert len(query.tokens) == 3

def test_right_bindings_for_each_term():
    query = these((child, brother)
                  for parent in this
                  for child in parent.children
                  for brother in parent.children
                  if child is not brother)

    child, brother = query.selection
    # XXX: This assume the order of the tokens is mantained!!!
    _this, child_token, brother_token = tuple(query.tokens)
    assert unboxed(child).binding is child_token
    assert unboxed(brother).binding is brother_token

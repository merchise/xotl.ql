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


from zope.interface import implementer

__docstring_format__ = 'rst'
__author__ = 'manu'


# This flag
__TEST_DESIGN_DECISIONS = True
__LOG = True


if __LOG:
    import sys
    from xoutil.compat import iterkeys_
    from xoutil.aop.classical import weave, _weave_before_method

    from xotl.ql.core import QueryParticlesBubble, QueryPart, _part_operations
    from xotl.ql.tests import logging_aspect

    # Weave logging aspect into every relevant method during testing
    aspect = logging_aspect(sys.stdout)
    weave(aspect, QueryParticlesBubble)
    for attr in iterkeys_(_part_operations):
        _weave_before_method(QueryPart, aspect, attr, '_before_')


if __TEST_DESIGN_DECISIONS:
    from xotl.ql.interfaces import IQueryPart
    from xotl.ql.core import QueryParticlesBubble

    class DesignDecisionTestCase(unittest.TestCase):
        def setUp(self):
            self.query_state_machine = query_state_machine = QueryParticlesBubble()
            self.query_context = context(query_state_machine)
            self.query_context.__enter__()
            self.query_context.bubble = query_state_machine


        def tearDown(self):
            self.query_context.__exit__(None, None, None)



    class DesignDecisionTests(DesignDecisionTestCase):
        '''
        Tests that are not functional. This suite only tests design
        decisions that may change over time; but which should not affect
        the result of ``these(<comprehension>)`` syntax *unless* there's
        a change in Query Language API.
        '''

        def test_yield_once_per_query(self):
            q = (a for c in this for b in c.bs for a in b.a)
            self.assertIsNotNone(next(q))
            with self.assertRaises(StopIteration):
                next(q)

            # TODO: Document how to obtain the queries
            qs = (a for i in range(3) for b in this('b' + str(i)) for a in b.a)
            for i in range(3):
                expected = this('b' + str(i)).a
                returned = unboxed(next(qs)).expression
                with context(UNPROXIFING_CONTEXT):
                    self.assertEqual(expected, returned)
            with self.assertRaises(StopIteration):
                next(qs)



        def test_plain_iter(self):
            t1 = next(iter(this))
            with context(UNPROXIFING_CONTEXT):
                self.assertTrue(IQueryPart.providedBy(t1),
                                      'When itering over a this instance we '
                                      'should get an IQueryPart object')

            t1 = next(parent for parent in this('parent'))
            self.assertEquals('parent', unboxed(unboxed(t1)._expression).name,
                              'The name of the QueryBuilderToken should be '
                              'the same as the name of the actual instance')

            t1 = next(parent for parent in this('parent').children)
            self.assertEquals('children', unboxed(unboxed(t1)._expression).name,
                              'The name of the QueryBuilderToken should be '
                              'the same as the name of the actual instance')


        def test_basic_queries_building(self):
            ok = self.assertEquals
            expr = next(parent.title + parent.name
                            for parent in this('parent')
                            if (parent.age > 32) & parent.married &
                               parent.spouse.alive)
            parts = self.query_state_machine.parts
            # The select part is at the top
            ok("this('parent').title + this('parent').name", str(parts[-1]))
            # Then the binding
            ok("((this('parent').age > 32) and this('parent').married) and "
               "this('parent').spouse.alive", str(parts[-2]))
            with self.assertRaises(IndexError):
                print(str(parts[-3]))


        def test_complex_query_building(self):
            parent, child = next((parent.title + parent.name,
                                  child.name + child.nick)
                                 for parent in this('parent')
                                    if (parent.age > 32) & parent.children
                                 for child in parent.children
                                    if child.age < 5)
            ok = self.assertEquals
            parts = self.query_state_machine.parts
            parent = this('parent')
            child = parent.children
            ok(str(child.name + child.nick), str(parts[-1]))
            ok(str(parent.title + parent.name), str(parts[-2]))
            ok(str(child.age < 5), str(parts[-3]))
            ok(str((parent.age > 32) & parent.children), str(parts[-4]))
            with self.assertRaises(IndexError):
                print(str(parts[-5]))


        def test_complex_intermingled_query(self):
            # See below, DesignDecisionRegressionTests
            pass


        def test_free_terms_are_not_captured(self):
            from xotl.ql.expressions import any_
            these(parent
                  for parent in this('parent')
                  if parent.name
                  if any_(this.children, this.age < 6))

            parts = self.query_state_machine.parts
            self.assertIs(1, len(parts))
            pname = this('parent').name
            with context(UNPROXIFING_CONTEXT):
                self.assertIn(pname, parts)


        def test_undetected_particles(self):
            from xotl.ql.expressions import any_
            these(parent
                  for parent in this('parent')
                  if any_(child for child in parent.children if child.age < 6))
            parts = self.query_state_machine.parts
            self.assertIs(0, len(parts))


        def test_rigth_bindings(self):
            these((parent, child)
                  for parent in this('parent')
                  if parent.children.updated_since(days=1)
                  for child in parent.children
                  if child.age < 4)
            parts = self.query_state_machine.parts
            bubble_tokens = self.query_state_machine.tokens
            with context(UNPROXIFING_CONTEXT):
                parent_token = next((token
                                     for token in bubble_tokens
                                     if token.expression == this('parent')),
                                    None)
                children_token = next((token
                                       for token in bubble_tokens
                                       if token.expression != this('parent')),
                                      None)
            child_age_filter = parts.pop(-1)
            parent_children_updated_filter = parts.pop(-1)
            with self.assertRaises(IndexError):
                parts.pop(-1)
            with context(UNPROXIFING_CONTEXT):
                child_age_term = child_age_filter.children[0]
                self.assertEqual(child_age_term.binding, children_token)

                # Note that: parent.children.updated_since(days=1)
                # is equivalent to invoke(parent.children.updated_since, days=1)
                parent_children_term = parent_children_updated_filter.children[0]
                self.assertEqual(parent_children_term.binding, parent_token)
                self.assertEqual(dict(days=1),
                                 parent_children_updated_filter.named_children)

        def test_tokens_as_names(self):
            next((parent, child)
                 for parent in this('parent')
                 if parent.children & parent.children.length() > 4
                 for child in parent.children
                 if child.age < 5)
            # The query has two filters:
            #
            #    this('parent').children & (count(this('parent').children) > 4)
            #    this('parent').children.age < 5
            #
            # If we regard every term `this('parent').children` as the *token*,
            # what would be the meaning of the first condition? How do we
            # distinguish from conditions over the named-token and the
            # expression that generates the token?
            # i.e in `for child in parent.children`, the `child` token
            # is *not* the same as the term `parent.children`.
            #
            # Now the token of the relevant query might help, but then the
            # machine should not strip those tokens from query-parts.



        def test_complex_query_building_with_dict(self):
            from xotl.ql.expressions import min_, max_
            d = {parent.age: (min_(child.age), max_(child.age))
                    for parent in this('parent')
                        if (parent.age > 32) & parent.children
                    for child in parent.children if child.age < 5}

            parts = self.query_state_machine.parts
            ok = lambda which: self.assertEqual(str(which), str(parts.pop(-1)))
            parent = this('parent')
            child = parent.children
            ok(parent.age)  # The key of the dict is the top-most expression
            ok(max_(child.age))
            ok(min_(child.age))
            ok(child.age < 5)
            ok((parent.age > 32) & parent.children)
            with self.assertRaises(IndexError):
                ok(None)


        def test_query_reutilization_design(self):
            from xotl.ql.expressions import is_a
            Person = "Person"
            persons = these(parent
                            for parent in this('parent')
                            if is_a(parent, Person))

            these(parent for parent in persons
                         if (parent.age < 35) & parent.children)


        def test_iters_produce_a_single_name(self):
            a1, a2 = next((p, p) for p in this)
            p1, p2 = next((p, t) for p in this for t in this)
            with context(UNPROXIFING_CONTEXT):
                self.assertEqual(a1, a2)
                self.assertNotEqual(p1, p2)


    class DesignDesitionsRegressionTests(DesignDecisionTestCase):
        def test_20121022_complex_intermingled_query(self):
            '''
            Tests that toy.type == 'laptop' does not get singled out
            of its containing expression.

            The following procedure is not current any more; but we leave it
            there for historical reasons. Since the introduction of "particle
            bubble" that captures all the parts and tokens, we have removed
            the :attr:`xotl.ql.interfaces.IQueryPart.tokens`.

               Slight variation over the same test of previous testcase but
               that shows how `|` that if we don't have the `tokens` params
               things will go wrong:

               - `parent.age > 32` will have `this('parent')` as its token

               - `child.age < 5` will have `this('parent').children` as its
                 token.

               - When building `(parent.age > 32) & (child.age < 5)` the
                 resultant part will have only `this('parent')` as the token,
                 and

               - `contains(child.toys, 'laptop')` will be attached to
                 `this('parent').children`, but this will create a stack in the
                 token for `child`, the stack will contain: ``child.age < 5``,
                 and ``contains(child.toys, 'laptop')``, for they don't merge.

               - Then, building ``... | contains(child.toys, 'laptop')`` will
                 be attached to `this('parent')` only! This will cause that the
                 token `this('parent').children` will be left with a stack of
                 two items that will be considered separate filters, which is
                 wrong!

               The solutions seems to be simply to make
               `this('parent').children` aware of parts that are generated. So
               :attr:`xotl.ql.core.QuerPart.tokens` is born.

            '''
            parent, child, toy = next((parent.title + parent.name,
                                       child.name + child.nick, toy.name)
                                      for parent in this('parent')
                                      for child in parent.children
                                      for toy in child.toys
                                      if (parent.age > 32) & (child.age < 5) |
                                         (toy.type == 'laptop'))
            parts = self.query_state_machine.parts
            parent = this('parent')
            child = parent.children
            ok = lambda x: self.assertEquals(str(x), str(parts.pop(-1)))
            toy = child.toys
            ok(toy.name)
            ok(child.name + child.nick)
            ok(parent.title + parent.name)
            ok((parent.age > 32) & (child.age < 5) | (toy.type == 'laptop'))
            with self.assertRaises(IndexError):
                print(ok(None))


    class DesignDesitionRegressionForgottenTokensAndFilters(DesignDecisionTestCase):
        '''
        Non-selected tokens should not be forgotten.

        This tests copycats most of the test_thesey_doesnot_messup_identities
        There's was two related bugs there:
           - There should be a token for rel
           - There should be a filter `is_instance(rel, Partnetship)`

        '''

        def test_is_a_partnership_is_not_forgotten(self):
            from itertools import izip
            next((person, partner)
                 for person, partner in izip(this('person'),
                                             this('partner'))
                 for rel in this('relation')
                 if rel.type == 'partnership'
                 if (rel.subject == person) & (rel.object == partner))
            parts = self.query_state_machine.parts
            tokens = self.query_state_machine.tokens
            ok = lambda x: self.assertEqual(str(x), str(parts.pop(-1)))
            person = this('person')
            partner = this('partner')
            rel = this('relation')
            self.assertIn(person, tokens)
            self.assertIn(partner, tokens)
            self.assertIn(rel, tokens)
            ok((rel.subject == person) & (rel.object == partner))
            ok(rel.type == 'partnership')
            with self.assertRaises(IndexError):
                ok(None)



        def test_worst_case_must_have_3_filters_and_3_tokens(self):
            from itertools import izip

            next(person
                 for person, partner in izip(this('person'),
                                             this('partner'))
                 for rel in this('relation')
                 if rel.type == 'partnership'
                 if rel.subject == person
                 if rel.object == partner
                 if partner.age > 32)
            parts = self.query_state_machine.parts
            tokens = self.query_state_machine.tokens
            ok = lambda x: self.assertEqual(str(x), str(parts.pop(-1)))
            person = this('person')
            partner = this('partner')
            rel = this('relation')
            self.assertIn(person, tokens)
            self.assertIn(partner, tokens)
            self.assertIn(rel, tokens)
            ok(partner.age > 32)
            ok(rel.object == partner)
            ok(rel.subject == person)
            ok(rel.type == 'partnership')
            with self.assertRaises(IndexError):
                ok(None)



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



if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main(verbosity=2)

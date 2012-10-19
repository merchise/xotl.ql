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

__docstring_format__ = 'rst'
__author__ = 'manu'


# This flag
__TEST_DESIGN_DECISIONS = True


if __TEST_DESIGN_DECISIONS:
    from xotl.ql.interfaces import IQueryPart

    class DesignDecisionTests(unittest.TestCase):
        '''
        Tests that are not functional. This suite only tests design
        decisions that may change over time; but which should not affect
        the result of ``these(<comprehension>)`` syntax *unless* there's
        a change in Query Language API.

        For instance, we test that comprehensions return always a
        :class:`xotl.ql.core.QueryPart` (or a tuple/dict of them).
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
            with context(UNPROXIFING_CONTEXT):
                token = expr.token
            parts = token._parts
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
            with context(UNPROXIFING_CONTEXT):
                pquery, cquery = parent.token, child.token
            pparts = pquery._parts
            ok("this('parent').title + this('parent').name",
               str(pparts[-1]))
            ok("(this('parent').age > 32) and this('parent').children",
               str(pparts[-2]))
            with self.assertRaises(IndexError):
                print(str(pparts[-3]))

            cparts = cquery._parts
            ok("this('parent').children.name + this('parent').children.nick",
               str(cparts[-1]))
            ok("this('parent').children.age < 5", str(cparts[-2]))
            with self.assertRaises(IndexError):
                print(str(cparts[-3]))


        def test_complex_intermingled_query(self):
            parent, child = next((parent.title + parent.name,
                                  child.name + child.nick)
                                    for parent in this('parent')
                                    for child in parent.children
                                    if (parent.age > 32) & (child.age < 5))
            ok = self.assertEquals
            with context(UNPROXIFING_CONTEXT):
                pquery, cquery = parent.token, child.token
            pparts = pquery._parts
            print(pparts)
            ok("this('parent').title + this('parent').name",
               str(pparts[-1]))
            # Notice that the second part is also present in the children.
            ok("(this('parent').age > 32) and (this('parent').children.age < 5)",
               str(pparts[-2]))
            with self.assertRaises(IndexError):
                print(str(pparts[-3]))

            cparts = cquery._parts
            print(cparts)
            ok("this('parent').children.name + this('parent').children.nick",
               str(cparts[-1]))
            ok("this('parent').children.age < 5", str(cparts[-2]))
            with self.assertRaises(IndexError):
                print(str(cparts[-3]))



        def test_complex_query_building_with_dict(self):
            from xotl.ql.expressions import min_, max_
            ok = self.assertEquals
            d = {parent.age: (min_(child.age), max_(child.age))
                    for parent in this('parent')
                        if (parent.age > 32) & parent.children
                    for child in parent.children if child.age < 5}

            parent, (min_child, max_child) = d.popitem()
            with context(UNPROXIFING_CONTEXT):
                pquery = parent.token
                parent = parent.expression
                minc_query = min_child.token
                min_child = min_child.expression
                maxc_query = max_child.token
                max_child = max_child.expression
            self.assertIs(maxc_query, minc_query)
            self.assertIsNot(pquery, maxc_query)
            ok("this('parent').age", str(parent))
            parts = pquery._parts
            ok("(this('parent').age > 32) and this('parent').children",
               str(parts[-2]))  # the selected `parent.age` was the last
            with self.assertRaises(IndexError):
                print(parts[-3])

            parts = maxc_query._parts
            top = parts.pop()
            ok("max(this('parent').children.age)", str(top))
            top = parts.pop()
            ok("min(this('parent').children.age)", str(top))
            top = parts.pop()
            ok("this('parent').children.age < 5", str(top))
            with self.assertRaises(IndexError):
                print(parts.pop())


        def test_query_reutilization_design(self):
            from xotl.ql.expressions import is_a
            Person = "Person"
            persons = these(parent for parent in this('parent')
                                if is_a(parent, Person))

            these(parent for parent in persons
                         if (parent.age < 35) & parent.children)


        def test_iters_produce_a_single_name(self):
            a1, a2 = next((p, p) for p in this)
            p1, p2 = next((p, t) for p in this for t in this)
            with context(UNPROXIFING_CONTEXT):
                self.assertEqual(a1, a2)
                self.assertNotEqual(p1, p2)



class TestUtilities(unittest.TestCase):
    def _test_class(self, Person):
        from xotl.ql.expressions import is_instance

        q = these((who for who in Person if who.age > 30),
                  limit=100)
        # We need to extract the who so that names matches
        who = domain = q.selection[0]
        q1 = these(who for who in domain if is_instance(who, Person)
                        if who.age > 30)

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

        self.assertEqual(slice(100), q.partition)


    def test_thesefy_good(self):
        from xotl.ql.core import thesefy

        @thesefy
        class Person(object):
            pass


        self._test_class(Person)


    def test_thesefy_meta_no_iter(self):
        from xotl.ql.core import thesefy

        class Meta(type):
            pass

        @thesefy
        class Person(object):
            __metaclass__ = Meta

        self._test_class(Person)


    def test_thesefy_good_meta(self):
        from xotl.ql.core import thesefy

        class Meta(type):
            def __iter__(self):
                from xoutil.objects import nameof
                return iter(this(nameof(self)))

        @thesefy
        class Person(object):
            __metaclass__ = Meta

        q = these(who for who in Person if who.age > 30)
        q1 = these(who for who in this('Person') if who.age > 30)
        with context(UNPROXIFING_CONTEXT):
            self.assertEqual(q.selection, q1.selection)



class TestThisQueries(unittest.TestCase):
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



if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main(verbosity=2)

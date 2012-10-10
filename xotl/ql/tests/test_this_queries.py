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
from xotl.ql.core import these, provides_all, provides_any
from xotl.ql.interfaces import IQuery

from collections import namedtuple

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

            young_parents = these(parent for parent in persons
                                        if (parent.age < 35) &
                                            parent.children)


        def test_iters_produce_a_single_name(self):
            a1, a2 = next((p, p) for p in this)
            p1, p2 = next((p, t) for p in this for t in this)
            with context(UNPROXIFING_CONTEXT):
                self.assertEqual(a1, a2)
                self.assertNotEqual(p1, p2)



class TestUtilities(unittest.TestCase):
    def test_thesefy(self):
        from xotl.ql.expressions import is_instance
        from xotl.ql.core import thesefy

        @thesefy
        class Person(object):
            pass

        q = these(who for who in Person if who.age > 30)
        q1 = these(who for who in this if is_instance(who, Person)
                        if who.age > 30)
        self.assertEqual(q, q1)


class TestThisQueries(unittest.TestCase):
    def test_most_basic_query(self):
        query = these(parent for parent in this('parent'))
        self.assertTrue(provides_any(query, IQuery))
        (p, ) = query.selection
        with context(UNPROXIFING_CONTEXT):
            self.assertEqual(p, this('parent'))


    def test_basic_queries(self):
        query = these((parent.title + parent.name, parent.age)
                        for parent in this('parent')
                        if parent.age < 40)
        self.assertTrue(provides_any(query, IQuery))

        (full_name, age) = query.selection
        full_name_expectation = this('parent').title + this('parent').name
        age_expectation = this('parent').age

        with context(UNPROXIFING_CONTEXT):
            self.assertEqual(full_name, full_name_expectation)
            self.assertEqual(age, age_expectation)

        filters = set(query.filters)
        filters_expectation = set((this('parent').age < 40, ))
        with context(UNPROXIFING_CONTEXT):
            self.assertEqual(filters, filters_expectation)



#    def test_qbuilder_relations(self):
#        a, b = next((p, p.age) for p in this('parent'))
#        self.assertIs(unboxed(a)._instance,
#                      unboxed(unboxed(b)._instance).parent)
#
#
#    def test_subqueries(self):
#        parent_age, children = next((parent.age, child) for parent in this('p')
#                                    for child in parent.children
#                                    if (parent.age > 32) & (child.age < 10))
#        self.assertEqual("this('p').age", str(parent_age))
#        self.assertEqual("this('p').children", str(children))
#        parent_binding = unboxed(parent_age).binding
#        child_binding = unboxed(children).binding
#        assert_ok = self.assertEqual
#        assert_ok("(this('p').age > 32) and (this('p').children.age < 10)",
#                  str(parent_binding))
#        assert_ok("(this('p').age > 32) and (this('p').children.age < 10)",
#                  str(child_binding))
#
#
#    def test_other_less_complex_iter(self):
#        person, book = next((person, book) for person in this('person')
#                                if person.age > 18
#                                for book in this('book')
#                                if book.owner == person)
#        with context(UNPROXIFING_CONTEXT):
#            person_binding = person.binding
#            book_binding = book.binding
#        assert_ok = self.assertEqual
#        assert_ok("this('person').age > 18", str(person_binding))
#        assert_ok("this('book').owner == this('person')", str(book_binding))
#
#
#    def test_indenpendent_results(self):
#        a, b = next((a, b) for a in this('a') for b in this('b')
#                            if a > 20 if b < 30)
#        with context(UNPROXIFING_CONTEXT):
#            a_binding = a.binding
#            b_binding = b.binding
#        self.assertEqual("this('a') > 20", str(a_binding))
#        self.assertEqual("this('b') < 30", str(b_binding))
#
#
#    def test_reusability_of_queries_as_generators(self):
#        from xotl.ql.expressions import is_instance
#        Book = 'Book'
#        Person = 'Person'
#        older = next(what for what in this('any') if what.age > 10)
#        books = these(book for book in older if is_instance(book, Book))
#        people = these(who for who in older if is_instance(who, Person))
#        everyone = these(who for who in older)
#        with context(UNPROXIFING_CONTEXT):
#            self.assertFalse(people == books)
#        books_binding = unboxed(books).binding
#        people_binding = unboxed(people).binding
#        all_binding = unboxed(everyone).binding
#        self.assertEqual("(this('any').age > 10) and "
#                         "(is_a(this('any'), Book))",
#                         str(books_binding))
#        self.assertEqual("(this('any').age > 10) and "
#                         "(is_a(this('any'), Person))",
#                         str(people_binding))
#        self.assertEqual("this('any').age > 10", str(all_binding))
#
#
#
#    def test_a_single_expression_as_selection1(self):
#        from xotl.ql.expressions import ExpressionTree
#        some = these((p.a + p.d) + (p.b + (p.c * -p.x))
#                        for p in this)
#        self.assertIsInstance(some, ExpressionTree)
#        parent_a = some.children[0].children[0]
#        binding_a = unboxed(parent_a).binding
#        self.assertIsNone(binding_a)
#
#
#    def test_a_single_expression_as_selection2(self):
#        from xotl.ql.expressions import ExpressionTree
#        some = these(parent.a + parent.b for parent in this)
#        self.assertIsInstance(some, ExpressionTree)
#        parent_a = some.children[0]
#        binding_a = unboxed(parent_a).binding
#        self.assertIsNone(binding_a)
#
#
#    def test_a_tuple_expression_as_selection(self):
#        from xotl.ql.expressions import ExpressionTree
#        a, b = these((parent.a + parent.b, parent.c + parent.a)
#                        for parent in this)
#        self.assertIsInstance(a, ExpressionTree)
#        self.assertIsInstance(b, ExpressionTree)
#        parent_a = a.children[0]
#        binding_a = unboxed(parent_a).binding
#        self.assertIsNone(binding_a)
#
#
#
#    def test_a_single_expression_as_selection_with_binding(self):
#        from xotl.ql.expressions import ExpressionTree
#        some = these(p.a + p.b for p in this('p') if p.a > 20)
#        self.assertIsInstance(some, ExpressionTree)
#        parent_a = some.children[0]
#        binding_a = unboxed(parent_a).binding
#        self.assertEqual("this('p').a > 20", str(binding_a))
#
#
#
#    def test_expression_as_selections(self):
#        from xotl.ql.expressions import count, ExpressionTree
#        from xotl.ql.core import These
#        some = these((p.age + 10, p,
#                      p.a + (p.b + count(p.x)))
#                        for p in this('p')
#                        if (p.age > 23) & (p.age < 45))
#        self.assertEqual((ExpressionTree, These, ExpressionTree),
#                         tuple(type(x) for x in some))
#        _a, p, _b = some
#        parent_age_binding = unboxed(p).binding
#        self.assertEqual("(this('p').age > 23) and (this('p').age < 45)",
#                         str(parent_age_binding))
#
#
#    def test_expressions_as_selections2(self):
#        from xotl.ql.expressions import startswith, ExpressionTree
#        who, book = these((who.age + 10, book.age + 10)
#                                for who in this('who')
#                                    if who.name == 'Pepe'
#                                for book in this('book')
#                                    if startswith(book.name, 'El'))
#        self.assertEqual((ExpressionTree, ExpressionTree),
#                         (type(who), type(book)))
#        i1 = who.children[0]
#        i1_binding = unboxed(i1).binding
#        i2 = book.children[0]
#        i2_binding = unboxed(i2).binding
#        self.assertEqual("this('who').name == Pepe", i1_binding)
#        self.assertEqual("startswith(this('book').name, El)", i2_binding)
#
#
#    def test_implicit_calling(self):
#        manus = these(who for who in this('who') if who.name.startswith('manu'))
#        binding = unboxed(manus).binding
#        self.assertEqual("this('who').name.startswith(manu)", str(binding))
#
#
#    def test_expressions_as_selections_with_grouping(self):
#        groups = these({parent.age + 10: (parent, child.x + 4, x)
#                            for parent in this('parent')
#                            for child in parent.children
#                                if (parent.age > 30) & (child.age > 10)
#                            for x in this('x')})
#        group, (p, c, x) = next(groups.iteritems())
#        p_binding = unboxed(p).binding
#        x_binding = unboxed(x).binding
#        self.assertEqual("this('parent').age + 10", str(group))
#        self.assertEqual("(this('parent').age > 30) and "
#                         "(this('parent').children.age > 10)",
#                         str(p_binding))
#        self.assertEqual("this('parent').children.x + 4", str(c))
#        self.assertIsNone(x_binding)
#
#
#    def test_expressions_as_selections_with_grouping_bad(self):
#        groups = these({parent.age + 10: (parent, child.x + 4, x)
#                            for parent in this('parent')
#                                if parent.age > 30
#                            for child in parent.children
#                                if (child.age > 10)
#                            for x in this('x')})
#        _group, (p, _c, _x) = next(groups.iteritems())
#        p_binding = unboxed(p).binding
#        with self.assertRaises(AssertionError):
#            self.assertEqual("(this('parent').age > 30) and "
#                             "(this('parent').children.age > 10)",
#                             str(p_binding))
#
#
#    def test_with_any_and_this(self):
#        from xotl.ql.expressions import is_instance, any_
#        four_stars = these(product for product in this('product')
#                                if is_instance(product, 'Product') &
#                                   any_(product.ratings,
#                                        this.rating == '****'))
#        binding = unboxed(four_stars).binding
#        self.assertEquals("(is_a(this('product'), Product)) and "
#                          "(any(this('product').ratings, (this.rating == ****)))",
#                          str(binding))
#
#
#    def test_this_never_gets_bound(self):
#        p = these(p for p in this if this.a > 10)
#        self.assertIsNone(unboxed(p).binding)
#        self.assertIsNone(unboxed(this).binding)
#
#
#    def test_lambda_expression(self):
#        from xotl.ql.expressions import count
#        old_enough = lambda who: who.age > 30
#        count_children = lambda who: count(who.children)
#        who, children = these((who, count_children(who))
#                                for who in this('who') if old_enough(who))
#        binding = unboxed(who).binding
#        self.assertEqual("this('who').age > 30", str(binding))
#        self.assertEqual("count(this('who').children)", str(children))
#
#
#
#    def test_arbitary_function(self):
#        from xotl.ql.expressions import call
#        postprocess = lambda who: who.age + 10
#        who = these(call(who, postprocess) for who in this('who'))
#        self.assertEqual(str(who), "call(this('who'), %r)" % postprocess)
#
#
#    def test_namedtuples(self):
#        result = namedtuple('result', "a b")
#        x = these(result(a=who.a, b=who.b) for who in this('who'))
#        self.assertIsInstance(x, result)
#        a = this('who').a
#        b = this('who').b
#        with context(UNPROXIFING_CONTEXT):
#            self.assertEqual(a, x.a)
#            self.assertEqual(b, x.b)
#
#
#    def test_simpledicts(self):
#        x = these(dict(a=who.a, b=who.b) for who in this('who'))
#        self.assertIsInstance(x, dict)
#        a = this('who').a
#        b = this('who').b
#        with context(UNPROXIFING_CONTEXT):
#            self.assertEqual(a, x['a'])
#            self.assertEqual(b, x['b'])
#
#    def test_single_attr_binding(self):
#        q = these(p for p in this('p') if p.valid)
#        self.assertEqual("this('p').valid", unboxed(q).binding)
#
#    def test_ranges_with_this(self):
#        queries = [x for y in range(10) for x in this('x')
#                    if y - 1 < x.age <= y]


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main(verbosity=2)

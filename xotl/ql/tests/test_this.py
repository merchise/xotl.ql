#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#----------------------------------------------------------------------
# xotl.ql.tests.test_this
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
# Created on May 25, 2012

from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        unicode_literals as _py3_unicode,
                        absolute_import as _py3_abs_import)

import unittest

from xoutil.context import context
from xoutil.proxy import UNPROXIFING_CONTEXT

from xotl.ql.core import this
from xotl.ql.expressions import _true, _false, ExpressionTree


__docstring_format__ = 'rst'
__author__ = 'manu'


class TestThisExpressions(unittest.TestCase):
    def test_this_anyattribute(self):
        'Tests that an unbound this instance has any attribute'
        self.assert_(this.a.b.c is not None)

    def test_this_anyattribute_str(self):
        'Tests that an unbound this instance has any attribute'
        self.assertEquals('this.a.b.c', str(this.a.b.c))
        self.assertEquals("this('z').a.b.c", str(this('z').a.b.c))

    def test_calling_functions(self):
        from xotl.ql.expressions import call
        expression = this.startswith('manu')
        self.assertIsInstance(expression, ExpressionTree)
        self.assertEqual("call(this.startswith, manu)",
                         str(expression))
        equiv_expr = call(this.startswith, 'manu')
        with context(UNPROXIFING_CONTEXT):
            self.assertEqual(equiv_expr, expression)

        # But the calling a these instance directly is not supported
        # (I think is not pretty)
        with self.assertRaises(TypeError):
            this('someone')('cannot', 'call', 'me')

    def test_tautology(self):
        self.assertIs(_true, this('parent') == this('parent'))
        self.assertIs(_true, this == this)
        self.assertIs(_false, this != this)
        self.assertIs(_false, this('parent') != this('parent'))

    def test_reverse_expressions(self):
        expr = 3 > "1" + this.x
        # Since numbers (3) don't implement the __gt__ for expression
        # expressions, python automatically reverses the expression to:
        #    ("1" + this.x) < 3
        # But since we SHOULD NOT reverse the + operator to `this.x + 1`,
        # since + may not be commutative (like in string concatenation).
        self.assertEqual("(1 + this.x) < 3", str(expr))

    def test_regression_test_calling_terms_directly(self):
        'Tests that invoke(term, ...) is equivalent to term(...)'
        from xotl.ql.expressions import invoke
        e1 = this('parent').children.updated_since(1, threshold=0.99)
        e2 = invoke(this('parent').children.updated_since, 1, threshold=0.99)
        with context(UNPROXIFING_CONTEXT):
            self.assertEqual(e1, e2)

    def test_simple_expression(self):
        expr = this('child').age < this('parent').age
        self.assertEqual("this('child').age < this('parent').age", str(expr))

    def test_all_ops(self):
        ok = self.assertEqual
        from operator import (eq, ne, lt, le, gt, ge, and_, or_, xor, add, sub,
                              mul, div, floordiv, mod, truediv, pow, lshift,
                              rshift, neg, abs, pos, invert)
        binary_tests = [(eq, '{0} == {1}'),
                        (ne, '{0} != {1}'),
                        (lt, '{0} < {1}'),
                        (gt, '{0} > {1}'),
                        (le, '{0} <= {1}'),
                        (ge, '{0} >= {1}'),
                        (and_, '{0} and {1}'),
                        (or_, '{0} or {1}'),
                        (xor, '{0} xor {1}'),
                        (add, '{0} + {1}'),
                        (sub, '{0} - {1}'),
                        (mul, '{0} * {1}'),
                        (div, '{0} / {1}'),
                        (truediv, '{0} / {1}'),
                        (floordiv, '{0} // {1}'),
                        (mod, '{0} mod {1}'),
                        (pow, '{0}**{1}'),
                        (lshift, '{0} << {1}'),
                        (rshift, '{0} >> {1}')]
        unary_tests = [(neg, '-{0}'),
                       (abs, 'abs({0})'),
                       (pos, '+{0}'),
                       (invert, 'not {0}')]
        for test, fmt in binary_tests:
            ok(fmt.format("this('p').age", "this('p').count"),
               str(test(this('p').age, this('p').count)))

        for test, fmt in unary_tests:
            ok(fmt.format("this('p').age"),
               str(test(this('p').age)))


class RegressionTests(unittest.TestCase):
    def test_this_SHOULD_NOT_be_singletons(self):
        # Making this instances singletons leads to subtle bugs in queries
        # and complicates the code just to avoid such complications:
        # An instance may be involved in a query::
        #    query = these(parent for parent in this('parent')
        #                    if parent.age > 40)
        #    query2 = these(parent for parent in this('parent')
        #                    if parent.age < 30)
        # If this('parent') were to return a singleton then the second
        # query could have overwritten the previous binding from the first
        # query; it took a bit of hackerish to avoid this:
        #    - Create a context and then skip the singleton-making code
        #      in such a context.
        # But since this instance are likely to be used always inside queries
        # the singleton stuff would not make improvement.
        # So it is best just to remove it.
        t1 = this('abc', parent=this('efc'))
        t2 = this('abc', parent=this('efc'))
        self.assertIsNot(t1, t2)

    def test_repr_this(self):
        self.assert_(repr(this).startswith('<this at 0x'))

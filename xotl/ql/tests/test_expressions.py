#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#----------------------------------------------------------------------
# xotl.ql.tests.test_expressions
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
# Created on May 28, 2012

from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        unicode_literals as _py3_unicode,
                        absolute_import as _py3_abs_import)

import unittest

from xoutil.context import context
from xoutil.proxy import UNPROXIFING_CONTEXT

from xotl.ql.expressions import q, eq, ne, lt, ExpressionTree


__docstring_format__ = 'rst'
__author__ = 'manu'


class TestSimpleExpression(unittest.TestCase):
    def test_eq(self):
        a = eq(1, 2)
        self.assertSetEqual(set([1, 2]), set(a.children))
        b = eq(3, 4)
        c = eq(a, b)
        self.assertSetEqual(set(c.children), set([a, b]))


    def test_un_eq(self):
        expression = eq(10, 34)
        self.assertIsNot(True, expression == eq(10, 34))
        self.assertIsInstance(expression == eq(10, 34), ExpressionTree)
        with context(UNPROXIFING_CONTEXT):
            self.assertIs(True, expression == eq(10, 34))


    def test_ne(self):
        a = ne(1, 2)
        self.assertSetEqual(set([1, 2]), set(a.children))
        b = ne(2, 3)
        c = ne(a, b)
        self.assertSetEqual(set(c.children), set([a, b]))


    def test_lt(self):
        a = lt(1, 2)
        self.assertSetEqual(set([1, 2]), set(a.children))
        b = lt(2, 3)
        c = lt(a, b)
        self.assertSetEqual(set(c.children), set([a, b]))


    def test_lt3(self):
        # TODO: [manu] Since we can't actually use the a < b < c,
        #       can we keep the AT_LEAST_TWO arity?
        expression = q(1) < q(2) < q(3)
        import dis
        dis.dis(self.test_lt3.im_func)
        self.assertNotEquals('(1 < 2) and (2 < 3)', str(expression))
        expression = (q(1) < q(2)) & (q(2) < q(3))
        self.assertEquals('(1 < 2) and (2 < 3)', str(expression))


    def test_qobjects(self):
        age = q(b'age')
        expr = age + q(10)
        self.assertEqual([str, int],
                         [type(child) for child in expr.children])


    def test_functors(self):
        from xotl.ql.expressions import startswith
        class Foobar(object):
            def startswith(self, other):
                return 1

        expr = startswith(q('something'), 'aaa')
        self.assertIsInstance(expr, ExpressionTree)

        expr = startswith(Foobar(), 'aaa')
        self.assertIs(1, expr)

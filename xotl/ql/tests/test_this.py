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

from xotl.ql.these import this, These, TheseType
from xotl.ql.util import named
from xotl.ql.expressions import _true, _false, in_, count, ExpressionTree

from xoutil.context import context
from xoutil.proxy import UNPROXIFING_CONTEXT

__docstring_format__ = 'rst'
__author__ = 'manu'


class TestThisExpressions(unittest.TestCase):
    def tearDown(self):
        TheseType._instances = {}

    def test_this_anyattribute(self):
        'Tests that an unbound this instance has any attribute'
        self.assert_(this.a.b.c is not None)


    def test_this_anyattribute_str(self):
        'Tests that an unbound this instance has any attribute'
        self.assertEquals('this.a.b.c', str(this.a.b.c))
        self.assertEquals("this('z').a.b.c", str(this('z').a.b.c))


    def test_this_dot_name(self):
        self.assertIsInstance(this, type(this.parent.name))


    def test_calling_functions(self):
        expression = this.parent.startswith('manu')
        self.assertIsInstance(expression, ExpressionTree)
        self.assertEqual("call(this.parent.startswith, manu)",
                         str(expression))
        with self.assertRaises(TypeError):
            this('someone')('cannot', 'call', 'me')


    def test_named(self):
        parent = this.parent
        child = parent.children
        self.assert_(isinstance(parent, named))
        self.assert_(isinstance(child, named))


    def test_tautology(self):
        self.assertIs(_true, this('parent') == this('parent'))
        self.assertIs(_true, this == this)
        self.assertIs(_false, this != this)
        self.assertIs(_false, this('parent') != this('parent'))


    def test_in_clause(self):
        parent, child = this('parent'), this('child')
        expr = in_(child, parent.children)
        expr2 = in_(this, this.children)
        with context(UNPROXIFING_CONTEXT):
            self.assertFalse(expr == expr2)


    def test_reverse_expressions(self):
        expr = 3 > "1" + this.x
        # Since numbers (3) don't implement the __gt__ for expression
        # expressions, python automatically reverses the expression to:
        #    ("1" + this.x) < 3
        # But since we SHOULD NOT reverse the + operator to `this.x + 1`,
        # since + may not be commutative (like in string concatenation).
        self.assertEqual("(1 + this.x) < 3", str(expr))


    def test_str_thisparent(self):
        self.assertEqual("this('parent')", str(this('parent')))


    def test_assert_unique_id(self):
        these = type(this)
        self.assertIs(this, these())
        self.assertIs(this('parent'), these('parent'))
        self.assertIs(this('parent').name, these(b'name',
                                                 parent=these('parent')))


    def test_simple_expression(self):
        expr = this('child').age < this('parent').age
        self.assertEqual("this('child').age < this('parent').age", str(expr))



    def test_autobindings_are_not_singletons(self):
        from xotl.ql.these import AutobindingThese
        t1 = AutobindingThese('a')
        t2 = AutobindingThese('b')
        self.assertIsNot(t1, t2)


    def test_init_with_binding(self):
        from xoutil.proxy import unboxed as u
        t = this('p', binding=this('p') > 33)
        binding = u(t).binding
        self.assertEqual("this('p') > 33", str(binding))

        # But directly calling the constructor won't work, this a feature of
        # this alone.
        t = These('p1', binding=this('p1').age > 78)
        binding = u(t).binding
        self.assertIsNone(binding)

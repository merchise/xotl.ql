#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#----------------------------------------------------------------------
# xotl.ql.tests.test_expressions
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
# Created on May 28, 2012

from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        unicode_literals as _py3_unicode,
                        absolute_import as _py3_abs_import)

import unittest

from xoutil.context import context
from xoutil.proxy import UNPROXIFING_CONTEXT

from xotl.ql.expressions import q


__docstring_format__ = 'rst'
__author__ = 'manu'


class BasicTests(unittest.TestCase):
    def test_expression(self):
        from xotl.ql.expressions import (count, ExpressionTree, or_, and_,
                                         pow_, lt, eq, add)
        expr = ((q(1) < 3) & (1 == q("1")) |
                (q("a") + q("b") ** 2 == q("x") + count("y")))
        expected = or_(and_(lt(1, 3), eq(1, "1")),
                       eq(add("a", pow_("b", 2)), add("x", count("y"))))
        self.assertIsInstance(expr, ExpressionTree)
        with context(UNPROXIFING_CONTEXT):
            self.assertTrue(expr == expected, "%s ---- %s" % (expected, expr))

    def test_target_procotol(self):
        class X(object):
            @staticmethod
            def _target_(self):
                return 1978

        x = X()
        expr = q(1) + x
        self.assertEqual((1, 1978), expr.children)
        self.assertEqual('1 + 1978', str(expr))

    def test_q_should_keep_it_self_in_expressions(self):
        'When :class:`xotl.ql.expressions.q` is involved in an expression '
        'it should remove itself from it'
        expr = q(1) + "1"
        self.assertEqual([int, unicode], [type(c) for c in expr.children])

        expr = 1 + q("1")
        self.assertEqual([int, unicode], [type(c) for c in expr.children])

        expr = q(1) + q("1")
        self.assertEqual([int, unicode], [type(c) for c in expr.children])

    def test_all_ops(self):
        ok = self.assertEqual
        from operator import (eq, ne, lt, le, gt, ge, and_, or_, xor, add, sub,
                              mul, div, floordiv, mod, truediv, pow, lshift,
                              rshift, neg, abs, pos, invert)
        from xotl.ql.expressions import count, min_, max_, all_, any_, length
        from xotl.ql.expressions import contains, is_instance, invoke, new
        from xotl.ql.expressions import startswith, endswith
        from xotl.ql.expressions import not_
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
                        (rshift, '{0} >> {1}'),
                        (endswith, "endswith('{0}', '{1}')"),
                        (contains, 'contains({0}, {1})'),
                        (is_instance, 'is_a({0}, {1})'),
                        (startswith, "startswith('{0}', '{1}')")]
        unary_tests = [(neg, '-{0}'),
                       (abs, 'abs({0})'),
                       (pos, '+{0}'),
                       (invert, 'not {0}'),
                       (not_, 'not {0}'),
                       (count, 'count({0})'),
                       (length, 'length({0})')]
        nary_tests = [(all_, 'all({0})'),
                      (any_, 'any({0})'),
                      (min_, 'min({0})'),
                      (max_, 'max({0})'),
                      (invoke, 'call({0}{1})'),
                      (new, 'new({0}{1})')]
        for test, fmt in binary_tests:
            ok(fmt.format("a", "b"),
               str(test(q('a'), 'b')))

        for test, fmt in unary_tests:
            ok(fmt.format("age"),
               str(test(q('age'))))

        args = (1, 2, 3, 4, 'a')
        args_str = ', '.join(str(a) for a in args)
        kwargs = {v: v for v in 'abcde'}
        kwargs_str = ', '.join('%s=%s' % (v, kwargs[v]) for v in kwargs)
        for test, fmt in nary_tests:
            if '{1}' in fmt:
                ok(fmt.format(args_str, ', ' + kwargs_str),
                   str(test(*args, **kwargs)))
            else:
                ok(fmt.format(args_str), str(test(*args)))

    def test_named_children(self):
        from xotl.ql.expressions import new
        self.assertEqual("new(object, a=1)", str(new('object', a=1)))

    def test_named_children_equivalence(self):
        from xotl.ql.expressions import new
        expr1 = new(object, a=1, b=3)
        expr2 = new(object, b=3, a=1)
        expr3 = new(object, b=1)
        with context(UNPROXIFING_CONTEXT):
            self.assertEqual(expr1, expr2)
            self.assertNotEqual(expr1, expr3)


class ExtensibilityTests(unittest.TestCase):
    def test_new_function(self):
        from xotl.ql.expressions import FunctorOperator, UNARY

        class SinFunction(FunctorOperator):
            '''
            The ``sin(arg)`` operation.
            '''
            _format = 'sin({0})'
            arity = UNARY
            _method_name = b'_sin'
        sin = SinFunction

        class ZeroObject(object):
            def _sin(self):
                return sin(360)

        zero = ZeroObject()
        expr = sin(zero)
        self.assertEquals("sin(360)", str(expr))


class RegressionTests(unittest.TestCase):
    def test_20120814_reversed_ops_should_work(self):
        expr = 1 + (2 + q(3))
        self.assertEquals('1 + (2 + 3)', str(expr))

    def test_20120822_reversed_eq_and_ne_should_compare_equal(self):
        expr = 1 == q("2")
        expr2 = q(1) == "2"
        with context(UNPROXIFING_CONTEXT):
            self.assertEqual(expr, expr2)

        # But we have not a reversing equality stuff.
        expr = 1 < q(2)
        expr2 = q(2) > 1
        with context(UNPROXIFING_CONTEXT):
            self.assertNotEqual(expr, expr2)

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

from xotl.ql.expressions import q


__docstring_format__ = 'rst'
__author__ = 'manu'


class BasicTests(unittest.TestCase):
    def test_q_should_keep_it_self_in_expressions(self):
        'When :class:`xotl.ql.expressions.q` is involved in an expression '
        'it should remove itself from it'
        expr = q(1) + "1"
        self.assertEqual([int, unicode], [type(c) for c in expr.children])

        expr = 1 + q("1")
        self.assertEqual([int, unicode], [type(c) for c in expr.children])

        expr = q(1) + q("1")
        self.assertEqual([int, unicode], [type(c) for c in expr.children])


class RegressionTests(unittest.TestCase):
    def test_20120814_reversed_ops_should_work(self):
        expr = 1 + (2 + q(3))
        self.assertEquals('1 + (2 + 3)', str(expr))

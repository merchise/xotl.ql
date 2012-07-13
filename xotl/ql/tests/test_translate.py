#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#----------------------------------------------------------------------
# xotl.ql.tests.test_translate
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
# Created on Jul 2, 2012


from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        unicode_literals as _py3_unicode,
                        absolute_import as _absolute_import)


import unittest
from xotl.ql.these import these, this


__docstring_format__ = 'rst'
__author__ = 'manu'



class TestTranslatorTools(unittest.TestCase):
    def test_traverse(self):
        from xotl.ql.translate import cotraverse_expression
        from xotl.ql.expressions import is_a, in_, all_
        who = these(who for who in this('w')
                        if all_(who.children,
                                in_(this, these(sub for sub in this('s')
                                                 if is_a(sub,
                                                         'Subs')))))
        is_a_nodes = cotraverse_expression(who,
                                           yield_node=lambda x: x.op == is_a,
                                           leave_filter=lambda _x: False)
        self.assertEquals(["is_a(this('s'), Subs)"],
                          [str(x) for x in is_a_nodes])



if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main(verbosity=2)

#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#----------------------------------------------------------------------
# xotl.ql.tests.test_ordering
#----------------------------------------------------------------------
# Copyright (c) 2013 Merchise Autrement and Contributors
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under
# the terms of the LICENCE attached in the distribution package.
#
# Created on 2013-03-28

from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        unicode_literals as _py3_unicode,
                        absolute_import as _py3_abs_imports)


from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        unicode_literals as _py3_unicode,
                        absolute_import as _py3_abs_import)

import unittest
import sys

from xotl.ql import this
from xotl.ql.core import these


__author__ = "Manuel Vázquez Acosta <mva.led@gmail.com>"
__date__   = "Thu Mar 28 15:13:59 2013"


class TestOrderingExpressions(unittest.TestCase):
    def test_ordering_expressions_are_buildable(self):
        from xotl.ql.expressions import max_
        these((parent for parent in this),
              ordering=lambda parent: +(max_(child.age for child in parent.children)/parent.age))

        these(((p, c) for p in this for c in p.children),
              ordering=lambda p, c: None)

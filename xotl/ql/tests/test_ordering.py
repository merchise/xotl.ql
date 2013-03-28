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

from xoutil.context import context
from xoutil.proxy import UNPROXIFING_CONTEXT, unboxed

from xotl.ql import this
from xotl.ql.core import these, provides_any
from xotl.ql.interfaces import IQueryObject
from xotl.ql.core import QueryParticlesBubble, QueryPart, _part_operations


from zope.interface import implementer

__author__ = "Manuel Vázquez Acosta <mva.led@gmail.com>"
__date__   = "Thu Mar 28 15:13:59 2013"


__LOG = False


if __LOG:
    import sys
    from itertools import chain
    from xoutil.compat import iterkeys_
    from xoutil.aop.classical import weave, _weave_around_method

    from xotl.ql.tests import logging_aspect

    # Weave logging aspect into every relevant method during testing
    aspect = logging_aspect(sys.stdout)
    weave(aspect, QueryParticlesBubble)
    for attr in iterkeys_(_part_operations):
        _weave_around_method(QueryPart, aspect, attr, '_around_')
    _weave_around_method(QueryPart, aspect, '__getattribute__', '_around_')



class TestOrderingExpressions(unittest.TestCase):
    def test_ordering_expressions_are_buildable(self):
        from xotl.ql.expressions import max_
        these((parent for parent in this),
              ordering=lambda parent: +(max_(child.age for child in parent.children)/parent.age))

        these(((p, c) for p in this for c in p.children),
              ordering=lambda p, c: None)

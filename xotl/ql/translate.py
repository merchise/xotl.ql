#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#----------------------------------------------------------------------
# xotl.ql.translate
#----------------------------------------------------------------------
# Copyright (c) 2012 Merchise Autrement and Contributors
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License (GPL) as published by the Free
# Software Foundation;  either version 3 of the  License, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Created on Jul 2, 2012

'''
The main purporses of this module are two:

- To provide common query/expression translation (co)routines from expressions
  to data store languages.

- To provide a testing bed for queries to retrieve real objects from somewhere
  (in this case the Python's).

'''

from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        unicode_literals as _py3_unicode,
                        absolute_import as _py3_abs_imports)

from xoutil.context import context
from xoutil.proxy import unboxed, UNPROXIFING_CONTEXT

from xotl.ql.expressions import ExpressionTree
from xotl.ql.interfaces import (IThese,
                                IQueryObject,
                                IQueryTranslator,
                                IQueryExecutionPlan)

__docstring_format__ = 'rst'
__author__ = 'manu'


_is_these = lambda who: IThese.providedBy(who)
_vrai = lambda _who: True
_none = lambda _who: False


def _iter_classes(accept=lambda x: True):
    '''Iterates over all the classes currently in Python's VM memory for which
    `accept(cls)` returns True.'''
    import gc
    return (ob for ob in gc.get_objects()
                if isinstance(ob, type) and accept(ob))



def _filter_by_pkg(pkg_name):
    '''Returns an `accept` filter for _iter_classes that only accepts
    classes of a given package name.'''
    def accept(cls):
        return cls.__module__.startswith(pkg_name)
    return accept



def _iter_objects(accept=lambda x: True):
    '''Iterates over all objects currently in Python's VM memory for which
    `accept(ob) returns True.'''
    import gc
    return (ob for ob in gc.get_objects
                if not isinstance(ob, type) and accept(ob))



def _instance_of(cls):
    '''Returns an `accept` filter for _iter_objects/_iter_classes that only
    accepts objects that are instances of `cls`.'''
    def accept(ob):
        return isinstance(ob, cls)
    return accept



def init(settings=None):
    '''Registers the implementation in this module as an IQueryTranslator for
    an object model we call "Python Object Model". Also we register this model
    as the default for the current :term:`registry`.

    .. warning::

       Don't call this method in your own code, since it will override all
       of your query-related configuration.

       This is only intended to allow testing of the translation common
       framework by installing query translator that searches over Python's VM
       memory.

    '''
    import sys
    from zope.component import getSiteManager
    from .interfaces import IQueryConfiguration, IQueryTranslator
    self = sys.modules[__name__]
    manager = getSiteManager()
    configurator = manager.queryUtility(IQueryConfiguration)
    if configurator:
        pass
    else:
        manager.registerUtility(self, IQueryConfiguration)
    manager.registerUtility(self, IQueryTranslator)



# -*- encoding: utf-8 -*-
# ---------------------------------------------------------------------
# xotl.ql.interfaces
# ---------------------------------------------------------------------
# Copyright (c) 2012-2015 Merchise Autrement and Contributors
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the LICENCE attached (see LICENCE file) in the distribution
# package.
#
# Created on Aug 23, 2012

'''Interfaces that describe the major types used in the Query Language API,
and some internal interfaces as well.


'''

from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)


from zope.interface import Interface, Attribute


class IQueryObject(Interface):
    '''The required API-level interface for query objects.

    Query objects provide access to the AST for the query.

    '''
    expression = Attribute('expression',
                           'Weak reference to the query expression.')

    def walk(self):
        '''Yield the nodes of the AST for the query.'''


class IQueryExecutionPlan(Interface):
    '''Required API-level interface for a query execution plan.

    '''
    query = Attribute('query',
                      'The original query object this plan was '
                      'built from.  Even if the translator was given a '
                      'query expression directly, like in most of our '
                      'examples, this must be a query object.')

    def __call__(self, **kwargs):
        '''Execution plans are callable.

        Return an `iterator`:term:.  The returned iterator must produce the
        objects retrieved from the query.  Also it must not be confused with
        other iterators returned and once exhausted it won't produce more
        objects.

        Translators are required to properly document the optional keyword
        arguments.  Positional arguments are not allowed.  All arguments must
        be optional.

        .. note:: The restrictions on the returned iterator make it easy to
           reason about it.  However obtaining a simple Cartesian product
           would require a call to `itertools.tee`:func:::

               >>> from xotl.ql import this
               >>> from xotl.ql.translation.py import naive_translation
               >>> query = naive_translation(which for which in this)

               >>> from itertools import tee
               >>> from six.moves import zip
               >>> product = zip(tee(query()))

           Doing a simple ``zip(query(), query())`` would work without error
           but between the first call to ``query()`` and the second the world
           might have changed the returned objects would not be the same.

        '''

    def __iter__(self):
        '''Execution plans are iterable.

        This is exactly the same as calling the plan without any arguments:
        ``plan()``.

        '''
        return self()

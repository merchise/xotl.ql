# -*- encoding: utf-8 -*-
#----------------------------------------------------------------------
# xotl.ql.interfaces
#----------------------------------------------------------------------
# Copyright (c) 2012-2014 Merchise Autrement and Contributors
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


class QueryObject(Interface):  # [TODO]
    '''The required API-level interface for query objects.

    Query objects provide access to the AST for the query.

    '''
    def walk(self):
        '''Yield the nodes of the AST for the query.'''


class QueryExecutionPlan(Interface):
    '''Required API-level interface for a query execution plan.

    '''
    query = Attribute('query',
                      'The original query object this plan was '
                      'built from.  Even if the translator was given a '
                      'query expression directly, like in most of our '
                      'examples, this must a query object.')

    def __call__(self, **kwargs):
        '''Execution plans are callable.

        Return an `iterator`:term:.  The returned iterator is only required to
        produce the objects retrieved from the query.  The only restriction is
        that it should be mixed with other iterators returned and once
        exhausted it won't produce more objects.

        So the following code is possible to build (in Python code) all pairs
        of objects (i.e Cartesian product)::

            # Let's have a translator
            >>> from xotl.ql.translation.py import naive_traslation as t
            >>> from xotl.ql import this

            >>> query = t(parent for parent in this)

            >>> list(zip(query(), query()))

        Translators are required to properly document the optional keyword
        arguments.  Positional arguments are not allowed.  All arguments must
        be optional.

        '''

    def __iter__(self):
        '''Execution plans are iterable.

        This is roughly a shortcut to calling it without any arguments:
        ``plan()``.

        '''
        return self()

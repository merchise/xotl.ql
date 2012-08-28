#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#----------------------------------------------------------------------
# xotl.ql.interfaces
#----------------------------------------------------------------------
# Copyright (c) 2012 Merchise Autrement
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under
# the terms of the LICENCE attached in the distribution package.
#
# Created on Aug 23, 2012

'''
Interfaces that describe the major types used in the Query Language API,
and some internal interfaces as well.
'''

from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        unicode_literals as _py3_unicode,
                        absolute_import as _py3_abs_imports)

from zope.interface import Interface, Attribute

__docstring_format__ = 'rst'
__author__ = 'manu'


__all__ = ('IOperator', 'IExpressionCapable',
           'ISyntacticallyReversibleOperation',
           'ISynctacticallyCommutativeOperation',
           'IExpressionTree', 'IQueryPart', 'IThese', 'IBoundThese',
           'ICallableThese', 'IQueryPartContainer', 'IQuery')



class IOperator(Interface):
    '''
    A description of an operator
    '''
    _format = Attribute('A string that contains the format that should be '
                        'used to obtain a human readable representation of '
                        'an expression that involves this operator.',
                        'The format string should contain one *positional* '
                        'arguments for each of the arguments it expects. '
                        'Notice this assumes a fixed number of arguments; for '
                        'the case of operations with a '
                        ':class:`variable <xotl.ql.expressions.N_ARITY>` '
                        'number of arguments, it should contain only one '
                        'positional argument that will be filled with all '
                        'arguments separated by commas.')
    _arity = Attribute('One of the classes :class:`~xotl.ql.expressions.UNARY`, '
                       ':class:`~xotl.ql.expressions.BINARY`, or '
                       ':class:`~xotl.ql.expressions.N_ARITY`')
    _method_name = Attribute('Name of the method that should be called upon '
                             'the first operand, much like python does for '
                             'its protocols',
                             'When instantiating an Operation (most likely '
                             'to build an instance of an '
                             ':class:`IExpressionTree`), this method *may* '
                             'be called on the first operand to allow '
                             'customization of how the expression is built. '
                             'If the first operand does not ahve this method '
                             'then instantion should build an expression tree '
                             'with this operation and all operands.')



class ISyntacticallyReversibleOperation(Interface):
    'Operations that follow a "reversed" protocol. Used for BINARY operators.'
    _rmethod_name = Attribute('Like :attr:`IOperator._method_name`, but for '
                              'the "reversed" operation.',
                              'This allows to implement some operation when '
                              'the first operand does not support it because '
                              'TypeError, but the second operand does., i.e: '
                              '`__radd__` for `1 + q("3")`.')



class ISynctacticallyCommutativeOperation(Interface):
    pass


class IExpressionCapable(Interface):
    'Objects that are allowed to be in expressions.'
    def __eq__(other):
        'Support for the binary `==` operator.'


    def __ne__(other):
        'Support for the binary `!=` operator.'


    def __lt__(other):
        'Support for the binary `<` operator.'

    def __gt__(other):
        'Support for the binary `>` operator.'


    def __le__(other):
        'Support for the binary `<=` operator.'


    def __ge__(other):
        'Support for the binary `>=` operator.'


    def __and__(other):
        'Support for the binary `&` operator.'


    def __rand__(other):
        'Support for the binary `&` operator.'


    def __or__(other):
        'Support for the binary `|` operator.'


    def __ror__(other):
        'Support for the binary `|` operator.'


    def __xor__(other):
        'Support for the binary `^` operator.'


    def __rxor__(other):
        'Support for the binary `^` operator.'


    def __add__(other):
        'Support for the binary `+` operator.'


    def __radd__(other):
        'Support for the binary `+` operator.'


    def __sub__(other):
        'Support for the binary `-` operator.'


    def __rsub__(other):
        'Support for the binary `-` operator.'


    def __mul__(other):
        'Support for the binary `*` operator.'


    def __rmul__(other):
        'Support for the binary `*` operator.'


    def __div__(other):
        'Support for the binary `/` operator.'
    __truediv__ = __div__


    def __rdiv__(other):
        'Support for the binary `/` operator.'
    __rtruediv__ = __rdiv__


    def __floordiv__(other):
        'Support for the binary `//` operator.'


    def __rfloordiv__(other):
        'Support for the binary `//` operator.'


    def __mod__(other):
        'Support for the binary `%` operator.'


    def __rmod__(other):
        'Support for the binary `%` operator.'


    def __pow__(other):
        'Support for the binary `**` operator.'


    def __rpow__(other):
        'Support for the binary `**` operator.'


    def __lshift__(other):
        'Support for the binary `<<` operator.'


    def __rlshift__(other):
        'Support for the binary `<<` operator.'


    def __rshift__(other):
        'Support for the binary `>>` operator.'


    def __rrshift__(other):
        'Support for the binary `>>` operator.'


    def __neg__():
        'Support for the unary `-` operator.'


    def __abs__():
        'Support for the `abs()` functor.'


    def __pos__():
        'Support for the unary `+` operator.'


    def __invert__():
        'Support for the `~` operator.'



class IExpressionTree(IExpressionCapable):
    '''A representation of an expression tree.

    It resembles a reduced AST for simple expressions. The expression tree has
    an `operation` attribute that holds a instance that describes the operation
    between the `children` of this expression. For instance, the expression: `3
    + 4**2 < 18983` would be encoded in a tree like::

       {operation: [<]        -- An object that represents the "<" operation
        children: (           -- children is always a tuple of "literals" or
                              -- other expressions.
           {operation: [+]
            children: (
                3,
                {operation: [**]
                 children: (4, 2)}
            )}
        )}

    '''

    operation = Attribute('An object that implements the :class:IOperator '
                          'interface')
    children = Attribute('A tuple that contains the operands. Operands may '
                         'be themselves other expressions')



class IQueryPart(IExpressionCapable):
    '''Represents a partial (but probably sound) expression that is been
    attached somehow to a query.

    When `these(<comprehension>)` an IQueryPartContainer object is generated
    internally to hold the query, but since we don't have the control of how
    Python does is execution of the comprehension, we substitute expression
    trees with "query part" objects.

    A query part behave as an expression but everytime a new query part is
    created the attached `query` object gets notified.

    '''
    query = Attribute('A reference to the query instance this part has been '
                      'attached to.',
                      'When queries are built, parts are created whenever '
                      'an expression tree is instantiated. But since queries '
                      'needs to record such a construction, parts invoke '
                      'the :meth:`IQueryPartContainer.created_query_part` '
                      'to allow the query object to be notified.')



class IThese(IExpressionCapable):
    '''IThese instances are meant to represent the *whole* universe of objects.

    These instances take place in expressions to create predicates about
    objects, such as::

        (this.age > 30) & (this.age < 40)

    '''

    def __iter__():
        'These instances should be iterable'


    def __getattribute__(attr):
        'Support for `this.attr[.attr2...]`'



class IBoundThese(IThese):
    'Bounded these instances'
    binding = Attribute('A these instance *may* be bound to another '
                        'expression.',
                        'Bound these instances are meant to represent '
                        'only those objects in the universe that matches '
                        'certain criteria. This attribute should be '
                        '*decidable* or None, but the means to decide '
                        'such a fact are beyond the scope of this interface.')



class ICallableThese(IThese):
    '''Some instances of IThese may actually represent a callable.

    For example, all attribute from this are callable these instances.
    '''
    def __call__(*args):
        'Support for callable these instances'



class IQueryPartContainer(Interface):
    def created_query_part(part):
        'Called whenever a new query part is created'



class IQuery(Interface):
    selection = Attribute('Either a tuple/dict of IThese/IExpressionTree '
                          'instances or single instance.')
    generator = Attribute('The instance from which this query was '
                          'created. Usually a These instance.')
    ordering = Attribute('A tuple of ordering expressions.')
    partition = Attribute('A slice object that indicates the slice of the '
                          'entire collection to be returned.')



class IQueryTranslator(Interface):
    '''
    A :term:`query translator`.
    '''

    def build_plan(query, **kwargs):
        '''Builds a query plan for a query. Returns an IQueryExecutionPlan.'''



class IQueryExecutionPlan(Interface):
    '''Represents the execution plan for a query.'''

    query = Attribute('The query for which is the plan.')

    def __call__():
        '''Executes the plan an retrieves a IDataCursor'''



class IDataCursor(Interface):
    def next():
        '''Returns the object at the cursor position and moves the cursor
        forward. If the cursor is out of objects raises `StopIteration`.

        '''



class IQueryConfiguration(Interface):
    '''A configuration object.'''

    default_translator_name = Attribute('The name to lookup in the components registry for a IQueryTranslator')

    def get_translator_for(**predicates):
        '''Get's the configured translator for a set of *predicates*


        :param app: A string that represents an application (or site)
                    within your system. You may need to merge several
                    applications within a system; each with it's own
                    database and query translator. Use this argument
                    to explicitly ask for the translator for a given
                    application.

        :param kind: A fully-qualified class name that uniquely
                     identify some object kind in your system and for
                     which you may need to specify a different translator.

        '''


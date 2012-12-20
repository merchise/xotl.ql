#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#----------------------------------------------------------------------
# xotl.ql.interfaces
#----------------------------------------------------------------------
# Copyright (c) 2012 Merchise Autrement and Contributors
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

from zope.interface import Interface, Attribute, invariant

__docstring_format__ = 'rst'
__author__ = 'manu'


__all__ = ('IOperator', 'IExpressionCapable',
           'ISyntacticallyReversibleOperation',
           'ISynctacticallyCommutativeOperation',
           'IExpressionTree', 'IQueryPart', 'ITerm', 'IBoundThese',
           'ICallableThese', 'IQueryPartContainer', 'IGeneratorToken')


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
    arity = Attribute('One of the classes :class:`~xotl.ql.expressions.UNARY`,'
                       ' :class:`~xotl.ql.expressions.BINARY`, or '
                       ':class:`~xotl.ql.expressions.N_ARITY`')
    _method_name = Attribute('Name of the method that should be called upon '
                             'the first operand, much like python does for '
                             'its protocols',
                             'When instantiating an Operation (most likely '
                             'to build an instance of an '
                             ':class:`IExpressionTree`), this method *may* '
                             'be called on the first operand to allow '
                             'customization of how the expression is built. '
                             'If the first operand does not have this method '
                             'then an expression with this operator and all '
                             'operands should be returned.')


class ISyntacticallyReversibleOperation(Interface):
    'Operations that follow a "reversed" protocol. Used for BINARY operators.'
    _rmethod_name = Attribute('Like :attr:`IOperator._method_name`, but for '
                              'the "reversed" operation.',
                              'This allows to implement some operation when '
                              'the first operand does not support it because '
                              'of TypeError, but the second operand does, '
                              'i.e: `__radd__` for `1 + q("3")`.')


class ISynctacticallyCommutativeOperation(Interface):
    '''Marks :class:`IOperator` instances that are *syntactically* commutative.

    This mark applies only to operators `==` and `!=`, which Python itself
    treats as commutative operations.

    In an expression like ``expr1 == expr2`` if the class of the `expr1` does
    not implements an `__eq__` method or returns `NotImplemented`, Python
    fallbacks to call the method `__eq__` for `expr2`.

    Notice that Python behaves differently when executing ``A + B``, i.e if `A`
    does not have an `__add__`, the method looked for in `B` is `__radd__`;
    i.e. the `+` operator is not commutative in general (for instance with
    strings.)

    Both `==` and `!=` are always commutative. That's why they need to test for
    equivalence in way in which the order operands does not matter.

    '''
    def equivalence_test(ones, another):
        '''
        Should return True if `operation(ones)` is equivalent to
        `operation(another)`.

        Operations like `==` use this method to ascertain that asking `a == b`
        is the same as asking `b == a`.
        '''

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
    '''A representation of an :term:`expression tree`.

    It resembles a reduced AST for simple expressions. The expression tree has
    an `operation` attribute that holds a instance that describes the operation
    between the `children` of this expression.

    '''

    operation = Attribute('An object that implements the '
                          ':class:`~xotl.ql.interfaces.IOperator` interface.')
    children = Attribute('A tuple that contains the operands. Operands may '
                         'be themselves other expression trees.')
    named_children = Attribute('A dictionary of named children. ',
                               '''This attribute allows to represent the Python
                               `**kwargs` idiom in the expressions so that
                               calling a function (see
                               :class:`~xotl.ql.expressions.invoke`) may invoke
                               represent the invocation of arbitrary python
                               functions.

                               ''')


class IQueryPart(IExpressionCapable):
    '''Represents a *possibly* partial (but sound) expression that is being
    constructed inside a query expression.

    Expression trees are powerful enough to capture the semantics of query
    parts. But, since we don't have the control of how Python does is execution
    of the comprehension, we employ query parts that behave just like
    expressions, but inform a :class:`IQueryParticlesBubble` that a new query
    part is being created.

    See the documentation for :class:`xotl.ql.core.QueryPart` to see the
    details of the procedure.

    '''
    expression = Attribute('The expression that this part stands for.'
                           'This expression should not be a query part '
                           'itself. The intention of this attribute '
                           'is to allow clients extract cleaned-up '
                           'versions of the expression without '
                           'the query-building related stuff.')


class ITerm(IExpressionCapable):
    '''ITerm instances are meant to represent the *whole* universe of objects.

    These instances take place in expressions to create predicates about
    objects, such as the `this` object in the following expression::

        (this.age > 30) & (this.age < 40)

    '''
    name = Attribute('The name of the instance.')
    parent = Attribute('Another ITerm instance from which self is drawn.')

    def __iter__():
        '''ITerm instances should be iterable. Also this should yield a single
        instance of a :class:`IQueryPart` whose :attr:`~IQueryPart.expression`
        should have a bound copy of `self`. The :attr:`~IBoundTerm.binding`
        should be made to an instance of a :class:`IGeneratorToken`, whose
        :attr:`~IGeneratorToken.expression` attribute should be `self`.
        '''

    def __getattribute__(attr):
        '''All ITerm instances support the creation of other instances just
        by accessing an attribute `this.anyattr`.

        This means that in order to access other *internal* attributes of the
        instance, an execution context is needed.

        :param attr: The name of the object to access.
        :type attr: unicode or str
        :returns: Another ITerm instance whose name is `attr` and whose parent
                  is `self`.
        '''

    def __call__(*args, **kwarg):
        '''When any term other that `this` is called, it should produce
        an appropiate expression like instance.
        '''


class IBoundTerm(ITerm):
    '''A term that is bound to a single :class:`IGeneratorToken` instance.

    Binding serves the purpose of identifying the *source* of a given term in a
    query. See :ref:`Terms versus Tokens <terms-vs-tokens>` for an example.
    '''
    binding = Attribute('The instance to which this term is bound to')


class IQueryParticlesBubble(Interface):
    '''
    An object used to capture newly created tokens and expressions that
    occur in a :term:`query expression`, when that query expression is used
    to create a :term:`query object`.
    '''
    def capture_token(token):
        '''Captures an emitted token.

        When a token is emitted if the last previously created part is a term
        that *is* the same as the :attr:`IGeneratorToken.expression`, then this
        last term should be removed from the particles collection.

        This is because in a query like::

            these((parent, child)
                  for parent in this
                  for child in parent.children)

        The `parent.children` emits itself as a query part and inmediatly it
        is transformed to a token.

        :param token: The emitted token
        :type token: :class:`IGeneratorToken`
        '''

    def capture_part(part):
        '''Captures an emitted query part.

        When a given part is captured, it might replace the lastly previously
        emitted parts if either of the following conditions hold:

        - The capture part *is* the same last emitted part.

        - The captured part is a term, and the last emitted part *is* its
          parent, then the parent part is replaced by the newly captured part.

        - The captured part is an expression and the last emitted part *is* one
          of its children (named or positional).

        The previous conditions are cycled while any of them hold against the
        particle at the "end" of the :attr:`particles` collection.

        Note that in an expression like ``invoke(some, a > b, b > c,
        argument=(c > d))`` before the whole expression is formed (and thus the
        part that represents it is captured), all of the arguments emitted
        particles, so we should remove those contained parts and just keep the
        bigger one that has them all.

        .. note::

           Checks **are** done with the `is` operator and not with `==`. Doing
           otherwise may lead to undesired results::

               these(parent.name for parent in this if parent.name)

           If `==` would be used, then the filter part `parent.name` would be
           lost.

        :param part: The emitted query part
        :type part: :class:`IQueryPart`
        '''

    parts = Attribute('Ordered collection of :class:`IQueryPart` instances '
                      'that were captured. ')
    tokens = Attribute('Ordered collection of :class:`IGeneratorToken` '
                       'tokens that were captured.')
    particles = Attribute('Ordered collection of either tokens or query parts '
                          'that were captured.',
                          'This property holds a list of all particles '
                          'not matter their types in the order they were '
                          'captured. This is intended to be used to '
                          'perform optimizations for translators. ')


class IGeneratorToken(Interface):
    '''In the :term:`query object`, a single :term:`generator token`.

    A generator token is a wrapper of the expression that is used inside a
    :term:`query object` as a named location from which to draw objects. It
    relates to the FROM clause in SQL, and to the ``<-`` operation in UnQL
    [UnQL]_.

    .. todo::

       Currently we only support :class:`ITerm` instances as generators, since
       allowing the `next` protocol directly over :term:`query objects <query
       object>` impedes using them as subqueries like in::

           q1 = these((a, b) for a in this for b in a.places)
           q2 = these(strformat('{0} has place {1}', a, b) for (a, b) in q1)

       The only way to include it would be by manually wrapping with a kind of
       `query()` function::

           q2 = these(strformat('{0} has place {1}', a, b) for (a, b) in query(q1))

       If this were to be allowed then a :term:`generator token` could be any
       type expression that may be regarded as collection of objects:

       - :class:`ITerm` instances
       - :class:`IQueryObject` instances.

       However, for the time being there's no such thing as a `query()`
       function.

    '''
    expression = Attribute('The instance from which this token was created. '
                           'Usually a :class:`ITerm` instance.')


class IQueryObject(Interface):
    '''A :term:`query object`.

    This objects captures a query by its selection, filters and generator
    tokens, and also provides ordering and partitioning features.

    '''
    selection = Attribute('Either a tuple/dict of :class:`ITerm` or '
                          ':class:`IExpressionTree` instances.')
    tokens = Attribute('Generator tokens that occur in the query',
                       '''When the :term:`query` is processed to create a
                       :term:`query object`, at least one :term:`generator
                       token` is created to represent a single, named
                       "location" from where objects are drawn. However a
                       :term:`query` may refer to several such locations. For
                       instance in the query::

                           these((book, author)
                                 for book in this
                                 for author in book.authors)

                       There are two generator tokens: a) ``this`` and b)
                       ``book.authors``. Those tokens relate to the FROM, and
                       possibly JOIN, clauses of the SQL language.

                       From the point of view of the query these tokens are
                       just *names*, how to use those names to interpret the
                       query is a task that is left to :term:`query translators
                       <query translator>`.

                       ''')
    filters = Attribute('A tuple of :class:`IExpressionTree` instances '
                        'that represent the WHERE clauses. They are logically '
                        'and-ed.')
    ordering = Attribute('A tuple of :ref:`ordering expressions '
                         '<ordering-expressions>`_.')
    partition = Attribute('A slice object that indicates the slice of the '
                          'entire collection to be returned.')
    params = Attribute('A dict containing other arguments to the query. '
                       'Some :term:`query translators <query translator>` '
                       'may make use of these to better decide how to '
                       'translate the query. For instance, you may '
                       'want have an OUTER JOIN, instead of a INNER JOIN '
                       'generated, and so on. '
                       'See :class:`~xotl.ql.core.these`.')

    def __iter__():
        '''
        Queries are iterable, but they **must** return ``self`` in this method.
        See :meth:`IQueryObject.next`.
        '''

    def next():
        '''
        Returns the next object in the cursor.

        Internally this should get the configure :class:`IQueryTranslator` and
        build the execution plan, then execute the plan to get the IDataCursor
        from which it can drawn objects from.
        '''


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

    default_translator_name = Attribute('The name to lookup in the components '
                                        'registry for a IQueryTranslator')

    def get_translator_for(**predicates):
        '''Get's the configured translator for a set of *predicates*.

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

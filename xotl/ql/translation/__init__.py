#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#----------------------------------------------------------------------
# xotl.ql.translate
#----------------------------------------------------------------------
# Copyright (c) 2012, 2013 Merchise Autrement and Contributors
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under
# the terms of the LICENCE attached in the distribution package.
#
# Created on Jul 2, 2012

'''The main purposes of this module are two:

- To provide common query/expression translation framework from query
  objects to data store languages.

- To provide a testing bed for queries to retrieve real objects from
  somewhere (in this case the Python's).

'''

from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        unicode_literals as _py3_unicode,
                        absolute_import as _py3_abs_imports)

from xoutil.context import context
from xoutil.proxy import UNPROXIFING_CONTEXT
from xoutil.modules import modulemethod
from xoutil.types import Unset
from xoutil.decorator import memoized_property
from xoutil.compat import iteritems_

from zope.interface import Interface

from xotl.ql.core import Term, GeneratorToken
from xotl.ql.expressions import _false, _true
from xotl.ql.expressions import OperatorType
from xotl.ql.expressions import ExpressionTree
from xotl.ql.expressions import UNARY, BINARY

from xotl.ql.expressions import EqualityOperator
from xotl.ql.expressions import NotEqualOperator
from xotl.ql.expressions import LogicalAndOperator
from xotl.ql.expressions import LogicalOrOperator
from xotl.ql.expressions import LogicalXorOperator
from xotl.ql.expressions import LogicalNotOperator
from xotl.ql.expressions import AdditionOperator
from xotl.ql.expressions import SubstractionOperator
from xotl.ql.expressions import DivisionOperator
from xotl.ql.expressions import MultiplicationOperator
from xotl.ql.expressions import FloorDivOperator
from xotl.ql.expressions import ModOperator
from xotl.ql.expressions import PowOperator
from xotl.ql.expressions import LeftShiftOperator
from xotl.ql.expressions import RightShiftOperator
from xotl.ql.expressions import LesserThanOperator
from xotl.ql.expressions import LesserOrEqualThanOperator
from xotl.ql.expressions import GreaterThanOperator
from xotl.ql.expressions import GreaterOrEqualThanOperator
from xotl.ql.expressions import ContainsExpressionOperator
from xotl.ql.expressions import IsInstanceOperator
from xotl.ql.expressions import LengthFunction
from xotl.ql.expressions import CountFunction
from xotl.ql.expressions import PositiveUnaryOperator
from xotl.ql.expressions import NegativeUnaryOperator
from xotl.ql.expressions import AbsoluteValueUnaryFunction
from xotl.ql.expressions import InvokeFunction

from xotl.ql.interfaces import (ITerm,
                                IGeneratorToken,
                                IExpressionTree,
                                IQueryTranslator)

__docstring_format__ = 'rst'
__author__ = 'manu'


def _instance_of(which):
    '''Returns an `accept` filter for :func:`_iter_objects` or
    :func:`_iter_classes` that only accepts objects that are instances of
    `which`; `which` may be either a class or an Interface
    (:mod:`!zope.interface`).

    '''
    def accept(ob):
        with context(UNPROXIFING_CONTEXT):
            return isinstance(ob, which) or (issubclass(which, Interface) and
                                             which.providedBy(ob))
    return accept


def cotraverse_expression(*expressions, **kwargs):
    '''Coroutine that traverses expression trees an yields every node that
    matched the `accept` predicate. If `accept` is None it defaults to accept
    only :class:`~xotl.ql.interface.ITerm` instances that have a non-None
    `name`.

    :param expressions: Several :term:`expression tree` objects (or
                        :term:`query objects <query object>`) to traverse.

    :param accept: A function that is passed every node found the trees that
                   must return True if the node should be yielded.

    Coroutine behavior:

    You may reintroduce both `expressions` and `accept` arguments by sending
    messages to this coroutine. The message may be:

    - A single callable value, which will replace `accept` immediately.

    - A single non-callable value, which will be considered *another*
      expression to process or (if it's a collection) several expressions.

      Notice this won't make `cotraverse_expression` to stop considering all
      the nodes from previous expressions.

    - A tuple consisting in `(*expressions, accept)` that will be treated like
      the previous case: expressions will be en-queued and accept will take
      effect immediately.

    - A dict that may have `exprs` and `accept` keys.

    The default `accept` behavior is to catch all **named** :class:`ITerm`
    instances in an expression. This might be useful to translators in order
    optimize de query plan.

    When introducing new expressions via messages to coroutine, it's guaranteed
    that previous expressions will be traversed completely before the new
    ones.

    '''
    from xoutil.types import is_collection
    from xoutil.objects import get_and_del_key
    is_expression = IExpressionTree.providedBy
    accept = get_and_del_key(kwargs, 'accept',
                             default=lambda x: _instance_of(ITerm)(x) and x.name)
    if kwargs != {}:
        raise TypeError('Invalid signature for cotraverse_expression')
    with context(UNPROXIFING_CONTEXT):
        queues = [[e] for e in expressions]
        while queues:
            queue = queues.pop(0)
            while queue:
                current = queue.pop(0)
                msg = None
                if accept(current):
                    msg = yield current
                if is_expression(current):
                    queue.extend(current.children)
                    named_children = current.named_children
                    queue.extend(named_children[key] for key in named_children)
                if msg:
                    exprs = None
                    if callable(msg):
                        accept = msg
                    elif isinstance(msg, tuple):
                        exprs, accept = msg[:-1], msg[-1]
                    elif isinstance(msg, dict):
                        exprs = msg.get('exprs', None)
                        accept = msg.get('accept', accept)
                    else:
                        exprs = msg
                    if exprs:
                        if is_collection(exprs):
                            queues.extend([e] for e in exprs)
                        else:
                            queues.append([exprs])


def cocreate_plan(query, **kwargs):
    '''**Not implemented yet**. The documentation provided is just an idea.

    Builds a :term:`query execution plan` for a given query that fetches
    objects from Python's VM memory.

    This function is meant to be general enough so that other may use
    it as a base for building their :term:`translators <query
    translator>`.

    It works like this:

    1. First it inspect the tokens and their relations (if a token is
       the parent of another). For instance in the query::

           query = these((parent, child)
                         for parent in this
                         if parent.children & (parent.age > 34)
                         for child in parent.children if child.age < 5)

       The `parent.children` generator tokens is *derived* from the
       token `this`, so there should be a relation between the two.

       .. todo::

          If we allow to have subqueries, it's not clear how to
          correlate tokens. A given token may be a whole query::

              p = these((parent, partner)
                        for parent in this('parent')
                        for partner, _ in subquery((partner, partner.depth())
                                            for partner in this
                                            if contains(partner.related_to,
                                                        parent)))

          Since all examples so far of sub-queries as generators
          tokens are not quite convincing, we won't consider that.

    '''
    pass

def cmp_terms(t1, t2, strict=False):
    '''Compares two terms in a partial order.

    This is a *partial* compare operator. A term `t1 < t2` if and only if `t1` is
    in the parent-chain of `t2`.

    If `strict` is False the comparison between expressions will be made with
    the `eq` operation; otherwise `is` will be used.

    If either `t1` or `t2` are generator tokens it's
    :attr:`~xotl.ql.interfaces.IGeneratorToken.expression` is used instead.

    Examples::

        >>> from xotl.ql.core import this, these
        >>> t1 = this('a').b.c
        >>> t2 = this('b').b.c.d
        >>> t3 = this('a').b

        >>> cmp_terms(t1, t3)
        1

        # But if equivalence is False neither t1 < t3 nor t3 < t1 holds.
        >>> cmp_terms(t1, t3, True)
        0

        # Since t1 and t2 have no comon ancestor, they are not ordered.
        >>> cmp_terms(t1, t2)
        0

        >>> query = these((child, brother)
        ...               for parent in this
        ...               for child in parent.children
        ...               for brother in parent.children
        ...               if child is not brother)

        >>> t1, t2, t3 = query.tokens

        >>> cmp_terms(t1, t2)
        -1

        >>> cmp_terms(t2, t3)
        0

    '''
    import operator
    if not strict:
        test = operator.eq
    else:
        test = operator.is_
    with context(UNPROXIFING_CONTEXT):
        if IGeneratorToken.providedBy(t1):
            t1 = t1.expression
        if IGeneratorToken.providedBy(t2):
            t2 = t2.expression
        if test(t1, t2):
            return 0
        else:
            t = t1
            while t and not test(t, t2):
                t = t.parent
            if t:
                return 1
            t = t2
            while t and not test(t, t1):
                t = t.parent
            if t:
                return -1
            else:
                return 0


def token_before_filter(tk, expr, strict=False):
    '''Partial order (`<`) compare function between a token (or term) and an
    expression.

    A token *is before* an expression if it is (or is before of) the binding of
    the terms in the expression.

    '''
    with context(UNPROXIFING_CONTEXT):
        def check(term):
            if tk is term.binding:
                return True
            else:
                return cmp_terms(tk, term.binding, strict) == -1
        return any(check(term) for term in cotraverse_expression(expr))


def cmp(a, b, strict=False):
    '''Partial compare function between tokens and expressions.

    Examples::

       >>> from xotl.ql import this, these
       >>> query = these((parent, child)
       ...               for parent in this
       ...               for child in parent.children
       ...               if parent.age > 34
       ...               if child.age < 6)

       >>> parent_token, children_token = query.tokens
       >>> expr1, expr2 = query.filters

       >>> cmp(parent_token, expr1)
       -1

       >>> cmp(children_token, parent_token)
       1

       >>> cmp(expr1, children_token)
       0

       >>> import functools
       >>> l = [expr1, expr2, parent_token, children_token]
       >>> l.sort(key=functools.cmp_to_key(cmp))
       >>> expected = [parent_token, expr1, children_token, expr2]
       >>> all(l[i] is expected[i] for i in (0, 1, 2, 3))
       True
    '''
    from ..interfaces import IExpressionCapable
    with context(UNPROXIFING_CONTEXT):
        if IGeneratorToken.providedBy(a) and IGeneratorToken.providedBy(b):
            return cmp_terms(a, b, strict)
        elif IGeneratorToken.providedBy(a) and IExpressionCapable.providedBy(b):
            return -1 if token_before_filter(a, b, strict) else 0
        elif IExpressionCapable.providedBy(a) and IGeneratorToken.providedBy(b):
            return 1 if token_before_filter(b, a, strict) else 0
        else:
            return 0

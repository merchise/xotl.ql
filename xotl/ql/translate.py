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
This modules introduces a :func:`fetch` function that allows to retrieves
objects the Python's garbage collector is tracking (i.e. all objects alive in
memory.)

The main purporses of this module are two:

- To provide common query/expression translation (co)routines from expressions
  to data store languages.

- To provide a testing bed for queries to retrieve real objects from somewhere
  (in this case the Python's).


Common tools for translating expressions
----------------------------------------

The fundamental tool for translating expressions is the function
:func:`cotraverse_expression`. It's a coroutine that allows to traverse the
entire expression tree (including bound :class:`~xotl.ql.core.These`
instances) and yields expression nodes and/or leaves that match a given
"predicate".

.. autofunction:: cotraverse_expression(expr, [inspect_node, yield_node, leave_filter])


Retrieving objects
------------------

This module provides a testbed facility to retrieves objects from the Python's
memory. It's by no means intended to be used in production, and the whole
point of its existence is to test the common translatations algorithms
provided, and also it help us in formalizing some concepts that may be useful
for other (but probably similar) stores.

.. autofunction:: fetch


'''

from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        unicode_literals as _py3_unicode,
                        absolute_import as _py3_abs_imports)

from xoutil.context import context
from xoutil.proxy import unboxed, UNPROXIFING_CONTEXT

from xotl.ql.expressions import ExpressionTree
from xotl.ql.core import These, these, this

__docstring_format__ = 'rst'
__author__ = 'manu'


__all__ = (b'cotraverse_expression', b'fetch', )



_is_these = lambda who: isinstance(who, These)
_vrai = lambda _who: True
_none = lambda _who: False



def cotraverse_expression(expr, inspect_node=_vrai, yield_node=_none,
                          leave_filter=_is_these):
    '''
    Traverses an expression and yields nodes that pass `yield_node` and the
    leaves that pass `leave_filter`.


    The first argument must be an instance of
    :class:`~xotl.ql.expression.ExpressionTree` or an instance of
    :class:`These`. In the second case, the :attr:`~These.binding` attribute
    is traversed (if any).

    :param expr: The expression to traverse.

    :param inspect_node: A function receiving a single argument (the current
                         node) that allows to prun the searching. If this
                         function returns True for a node in the expression
                         tree, then the it's child will be inspected.

    :param yield_node: A function that receives a single argument (the current
                       node) and should return True if we must yield the node.
                       There's no relation with the `inspect_node` parameter,
                       you may dissallow traversing through a node, but let
                       it be yielded to the calling routine.

    :param leave_filter: A function that receives a single argument (the
                         current non-expression node) and should True if we
                         must yield the leave to the calling routine.

    This function works as a coroutine, i.e, you may send messages to it while
    its running. The protocol is as follows:

    - After every object received (yielded), you may pass **up to three** new
      functions to replace `inspect_node`, `yield_node` and `leave_filter`
      respectively.

        >>> from xotl.ql.expressions import is_a, all_, in_
        >>> from xotl.ql.core import these, this
        >>> who = these(who for who in this('w')
        ...                 if all_(who.children,
        ...                         in_(this, these(sub for sub in this('s')
        ...                                         if is_a(sub,
        ...                                                 'Subs')))))

    Everytime we see a new These instance, if it has a binding we traverse it
    as well.

    Example: one may be interested in `is_a` nodes::

        >>> is_a_nodes = cotraverse_expression(who,
        ...                  yield_node=lambda x: x.op == is_a,
        ...                  leave_filter=_none)
        >>> [str(x) for x in is_a_nodes]
        ["is_a(this('s'), Subs)"]

    '''
    import types
    if isinstance(expr, These):
        dejavu = [unboxed(expr).root_parent]
        expr = unboxed(expr).binding
    else:
        dejavu = []
    if expr:
        assert isinstance(expr, ExpressionTree)
        queue = [expr]
        while queue:
            node = queue.pop(0)
            message = None
            with context(UNPROXIFING_CONTEXT):
                if isinstance(node, ExpressionTree):
                    if inspect_node(node):
                        queue.extend(node.children)
                    if yield_node(node):
                        message = yield node
                elif leave_filter(node) and node not in dejavu:
                    dejavu.append(node)
                    message = yield node
                if isinstance(node, These):
                    parent = node.root_parent
                    if parent not in dejavu:
                        dejavu.append(parent)
                        binding = node.binding
                        if binding:
                            queue.append(binding)
            if message:
                if not isinstance(message, tuple):
                    message = (message, None, None)
                new_inspect_node = message[0]
                new_yield_node = message[1] if len(message) > 1 else None
                new_leave_filter = message[2] if len(message) > 2 else None
                if new_inspect_node:
                    assert isinstance(new_inspect_node, (types.MethodType,
                                                         types.FunctionType))
                    inspect_node = new_inspect_node
                if new_yield_node:
                    assert isinstance(new_yield_node, (types.MethodType,
                                                       types.FunctionType))
                    yield_node = new_yield_node
                if new_leave_filter:
                    assert isinstance(new_leave_filter, (types.MethodType,
                                                         types.FunctionType))
                    leave_filter = new_leave_filter



def replace_known_functions(expr):
    '''
    Traverses the expression and replaces all calls to known functions to the
    expressions that directly use the function:
    '''
    pass



def fetch(expr, order=None, partition=None):
    '''
    Generates all the objects that match a given query.

    :param expr: A query comprehesion or the result of calling
                  :func:`~xotl.ql.core.these` over a comprehension.

    :param order: Ordering scheme: Either a single expression in which case it
                  should either: ``+this`` or ``-this``, or a tuple of
                  expressions each of which may in the form of
                  ``[+-]this.column_<number>``.

                  **Not yet implemented**

    :param partition: A slice that marks the start, end and step. The normal
                      interpretation for slices applies.
    '''
    pass

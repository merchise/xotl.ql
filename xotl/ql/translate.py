#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#----------------------------------------------------------------------
# xotl.ql.translate
#----------------------------------------------------------------------
# Copyright (c) 2012 Merchise Autrement and Contributors
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under
# the terms of the LICENCE attached in the distribution package.
#
# Created on Jul 2, 2012

'''
The main purposes of this module are two:

- To provide common query/expression translation framework from query objects
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

from zope.interface import Interface

from xotl.ql.expressions import ExpressionTree
from xotl.ql.interfaces import (ITerm,
                                IExpressionTree,
                                IQueryObject,
                                IQueryTranslator,
                                IQueryExecutionPlan)

__docstring_format__ = 'rst'
__author__ = 'manu'


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


def _instance_of(which):
    '''Returns an `accept` filter for _iter_objects/_iter_classes that only
    accepts objects that are instances of `which`; `which` may be either
    a class or an Interface (:mod:`zope.interface`).'''
    def accept(ob):
        return isinstance(ob, which) or (issubclass(which, Interface) and
                                         which.providedBy(ob))
    return accept


def cofind_tokens(*expressions, **kwargs):
    '''
    Coroutine that traverses expression trees an yields every node that matched
    the `accept` predicate. If `accept` is None it defaults to accept only
    :class:`~xotl.ql.interface.ITerm` instances that have a non-None `name`.

    Coroutine behavior:

    You may reintroduce both `expr` and `accept` arguments by sending messages
    to this coroutine. The message may be:

    - A single callable value, which will replace `accept`.

    - A single non callable value, which will be considered *another*
      expression to process. Notice this won't make `cofind_tokens` to stop
      considering all the nodes from previous expressions. However, the
      expression might be explored before other later generated children
      of the previous expressions.

    - A tuple consisting in `(expr, accept)` that will be treated like the
      previous cases.

    - A dict that may have `expr` and `accept` keys.

    The default behavior helps to catch all named ITerm instances in an
    expression. This is useful for finding every "name" in a query, which may
    no appear in the query selection. For instance we, may have a model that
    relates Person objects indirectly via a Relation object::

        >>> from xotl.ql.core import thesefy
        >>> @thesefy('person')
        ... class Person(object):
        ...     pass

        >>> @thesefy('relation')
        ... class Relation(object):
        ...    pass

    Then, for the following query::

        >>> from xotl.ql.core import these
        >>> from itertools import izip
        >>> query = these((person, partner)
        ...               for person, partner in izip(Person, Person)
        ...               for rel in Relation
        ...               if (rel.subject == person) & (rel.obj == partner))

    if we need to find every single named term in the filters of the query,
    we would see that there are seven:

        - `person`, `partner` and `rel` (as given by the `is_instance(...)`
          filters ``@thesefy`` injects)

        - `rel.subject`, `person`, `rel.obj` and `partner` in the explicit
          filter.

        >>> len(list(cofind_tokens(*query.filters)))
        7
    '''
    is_expression = IExpressionTree.providedBy
    accept = kwargs.get('accept', lambda x: _instance_of(ITerm)(x) and x.name)
    with context(UNPROXIFING_CONTEXT):
        queue = list(expressions)
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
                if callable(msg):
                    accept = msg
                elif isinstance(msg, tuple):
                    expr, accept = msg
                    queue.append(expr)
                elif isinstance(msg, dict):
                    expr = msg.get('expr', None)
                    if expr:
                        queue.append(expr)
                    accept = msg.get('accept', accept)
                else:
                    queue.append(msg)


def cocreate_plan(query, **kwargs):
    '''**Not implemented yet**. The documentation provided is just an idea.

    Builds a :term:`query execution plan` for a given query that fetches
    objects from Python's VM memory.

    This function is meant to be general enough so that other may use it as a
    base for building their :term:`translators <query translator>`.

    It works like this:

    1. First it inspect the tokens and their relations (if a token is the
       parent of another). For instance in the query::

           query = these((parent, child)
                         for parent in this
                         if parent.children & (parent.age > 34)
                         for child in parent.children if child.age < 5)

       The `parent.children` generator tokens is *derived* from the token
       `this`, so there should be a relation between the two.

       .. todo::

          If we allow to have subqueries, it's not clear how to correlate
          tokens. A given token may be a whole query::

              p = these((parent, partner)
                        for parent in this('parent')
                        for partner, _ in subquery((partner, partner.depth())
                                            for partner in this
                                            if contains(partner.related_to,
                                                        parent)))

         Since all examples so far of sub-queries as generators tokens are not
         quite convincing, we won't consider that.

    '''
    pass


def init(settings=None):
    '''Registers the implementation in this module as an IQueryTranslator for
    an object model we call "Python Object Model". Also we register this model
    as the default for the current :term:`registry`.

    .. warning::

       Don't call this method in your own code, since it will override all
       of your query-related configuration.

       This is only intended to allow testing of the translation common
       framework by configuring query translator that searches over Python's VM
       memory.

    '''
    import sys
    from zope.component import getSiteManager
    from zope.interface import directlyProvides
    from .interfaces import IQueryConfiguration
    self = sys.modules[__name__]
    directlyProvides(self, IQueryConfiguration, IQueryTranslator)
    manager = getSiteManager()
    configurator = manager.queryUtility(IQueryConfiguration)
    if configurator:
        pass
    else:
        manager.registerUtility(self, IQueryConfiguration)
    manager.registerUtility(self, IQueryTranslator)

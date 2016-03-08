#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# ---------------------------------------------------------------------
# xotl.ql.core
# ---------------------------------------------------------------------
# Copyright (c) 2012-2016 Merchise Autrement and Contributors
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under
# the terms of the LICENCE attached in the distribution package.
#
# Created on May 24, 2012


'''The query language core.

'''

from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)


import types
from xoutil import Unset
from collections import MappingView, Mapping


from xotl.ql import interfaces


class Universe(object):
    '''The class of the `this`:obj: object.

    The `this` object is simply a name from which objects can be drawn in a
    query.

    '''
    def __new__(cls):
        res = getattr(cls, 'instance', None)
        if not res:
            res = super(Universe, cls).__new__(cls)
            cls.instance = res
        return res

    def __getitem__(self, key):
        return self

    def __getattr__(self, name):
        return self

    def __iter__(self):
        return self

    def next(self):
        raise StopIteration
    __next__ = next

this = Universe()


RESERVED_ARGUMENTS = (
    'limit', 'offset', 'groups', 'order', 'get_name', 'qst', '_frame'
)


class QueryObject(object):
    frame_type = 'xotl.ql.core.Frame'

    def __init__(self, qst, _frame, **kwargs):
        self.qst = qst
        self._frame = _frame
        if any(name in RESERVED_ARGUMENTS for name in kwargs):
            raise TypeError('Invalid keyword argument')
        self.expression = kwargs.pop('expression', None)
        for attr, val in kwargs.items():
            setattr(self, attr, val)

    def get_name(self, name, only_globals=False):
        if not only_globals:
            res = self._frame.f_locals.get(name, Unset)
        else:
            res = Unset
        if res is Unset:
            res = self._frame.f_globals.get(name, Unset)
        if res is not Unset:
            return res
        else:
            raise NameError(name)

    @property
    def locals(self):
        return self._frame.f_locals

    @property
    def globals(self):
        return self._frame.f_globals


def get_query_object(generator,
                     query_type='xotl.ql.core.QueryObject',
                     frame_type=None,
                     **kwargs):
    '''Get the query object from a query expression.

    '''
    from ._util import import_object
    from xotl.ql.revenge import Uncompyled
    uncompiled = Uncompyled(generator)
    gi_frame = generator.gi_frame
    QueryObjectType = import_object(query_type)
    FrameType = import_object(frame_type or QueryObjectType.frame_type)
    return QueryObjectType(
        uncompiled.qst,
        FrameType(gi_frame.f_locals, gi_frame.f_globals),
        expression=generator,
        **kwargs
    )


parse_query = get_query_object
# Alias to the old API.
these = get_query_object


def get_predicate_object(func, predicate_type='xotl.ql.core.QueryObject',
                         frame_type=None, **kwargs):
    from ._util import import_object
    from .revenge import Uncompyled
    uncompiled = Uncompyled(func)
    PredicateClass = import_object(predicate_type)
    FrameClass = import_object(frame_type or PredicateClass.frame_type)
    return PredicateClass(
        uncompiled.qst,
        FrameClass(_get_closure(func), func.__globals__),
        predicate=func,
        **kwargs
    )


def normalize_query(which, **kwargs):
    '''Ensure a query object.

    If `which` is a query expression (more precisely a generator object) it is
    passed to `get_query_object`:func: along with all keyword arguments.

    If `which` is not a query expression it must be a `query object`:term:,
    other types are a TypeError.

    '''
    from types import GeneratorType
    if isinstance(which, GeneratorType):
        return get_query_object(which, **kwargs)
    else:
        if not isinstance(which, interfaces.QueryObject):
            raise TypeError('Query object expected, but object provided '
                            'is not: %r' % type(which))
        return which


def thesefy(target):
    '''Allow an object to participate in queries.

    Example as a wrapper::

        class People(object):
            # ...
            pass

        query = (who for who in thesefy(People))

    Example as a decorator::

        @thesefy
        class People(object):
            pass

        query = (who for who in People)

    If your classes already support the iterable protocol (i.e implement
    ``__iter__``) this does nothing.

    '''
    if getattr(target, '__iter__', None):
        return target

    class new_meta(type(target)):
        def __iter__(self):
            return (x for x in this if isinstance(x, self))

        def next(self):
            raise StopIteration
        __next__ = next

    from xoutil.objects import copy_class
    new_class = copy_class(target, meta=new_meta)
    return new_class


class Frame(object):
    def __init__(self, locals, globals, **kwargs):
        self.auto_expand_subqueries = kwargs.pop('auto_expand_subqueries',
                                                 True)
        self.f_locals = _FrameView(locals)
        self.f_globals = _FrameView(globals)
        self.f_locals.owner = self.f_globals.owner = self


class _FrameView(MappingView, Mapping):
    def __contains__(self, key):
        try:
            self[key]
        except KeyError:
            return False
        else:
            return True

    def __getitem__(self, key):
        res = self._mapping[key]
        if self.owner.auto_expand_subqueries and key == '.0':
            return sub_query_or_value(res)
        else:
            return res

    def get(self, key, default=None):
        res = self._mapping.get(key, default)
        if self.owner.auto_expand_subqueries and key == '.0':
            return sub_query_or_value(res)
        else:
            return res

    def __iter__(self):
        return iter(self._mapping)


def _get_closure(obj):
    assert isinstance(obj, types.FunctionType)
    if obj.__closure__:
        return {
            name: cell.cell_contents
            for name, cell in zip(obj.__code__.co_freevars, obj.__closure__)
        }
    else:
        return {}


def sub_query_or_value(v):
    if isinstance(v, types.GeneratorType) and v.gi_code.co_name == '<genexpr>':
        return get_query_object(v)
    else:
        return v

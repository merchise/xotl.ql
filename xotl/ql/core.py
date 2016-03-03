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
    def __init__(self, qst, _frame, **kwargs):
        self.qst = qst
        self._frame = _frame
        self.partition = None
        if any(name in RESERVED_ARGUMENTS for name in kwargs):
            raise TypeError('Invalid keyword argument')
        self.__dict__.update(kwargs)

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

    def limit_by(self, limit):
        '''Return a new query object limited by limit.

        If this query object already has a limit it will be ignore.

        '''
        raise NotImplementedError

    def offset(self, offset):
        '''Return a new query object with a new offset.'''
        raise NotImplementedError


def get_query_object(generator, **kwargs):
    '''Get the query object from a query expression.

    '''
    from xotl.ql.revenge import Uncompyled
    uncompiled = Uncompyled(generator)
    gi_frame = generator.gi_frame
    return QueryObject(
        uncompiled.qst,
        Frame(gi_frame.f_locals, gi_frame.f_globals, gi_frame.f_builtins),
        expression=generator,
        **kwargs
    )


def get_predicate_object(func, **kwargs):
    from xotl.ql.revenge import Uncompyled
    uncompiled = Uncompyled(func)
    return QueryObject(
        uncompiled.qst,
        Frame(_get_closure(func), func.__globals__, {}),
        predicate=func,
        **kwargs
    )

# Alias to the old API.
these = get_query_object


def normalize_query(which, **kwargs):
    '''Ensure a query object.

    If `which` is a query expression (more precisely a generator object) it is
    passed to `get_query_object`:func:.  Otherwise it should be a query
    object.

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
    def __init__(self, locals, globals, builtins):
        self.f_locals = AccesableMappingView(locals)
        self.f_globals = AccesableMappingView(globals)
        self.f_builtins = AccesableMappingView(builtins)


class AccesableMappingView(MappingView, Mapping):
    def __contains__(self, key):
        try:
            self[key]
        except KeyError:
            return False
        else:
            return True

    def __getitem__(self, key):
        return self._mapping[key]

    def get(self, key, default=None):
        return self._mapping.get(key, default)

    def __iter__(self):
        return iter(self._mapping)


def _get_closure(obj):
    import types
    assert isinstance(obj, types.FunctionType)
    if obj.__closure__:
        return {
            name: cell.cell_contents
            for name, cell in zip(obj.__code__.co_freevars, obj.__closure__)
        }
    else:
        return {}

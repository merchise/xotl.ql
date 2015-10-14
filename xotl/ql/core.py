#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# ---------------------------------------------------------------------
# xotl.ql.core
# ---------------------------------------------------------------------
# Copyright (c) 2012-2015 Merchise Autrement and Contributors
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


class universe(object):
    '''The class of the `this`:obj: object.

    The `this` object is simply a name from which objects can be drawn in a
    query.

    '''
    def __new__(cls):
        res = getattr(cls, 'instance', None)
        if not res:
            res = super(universe, cls).__new__(cls)
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

this = universe()


def get_query_object(generator, **kwargs):
    '''Get the query object from a query expression.

    '''
    pass

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
        from xotl.ql.interfaces import QueryObject
        if not all(hasattr(which, attr) for attr in QueryObject.names()):
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
            return self

        def next(self):
            raise StopIteration

    from xoutil.objects import copy_class
    new_class = copy_class(target, meta=new_meta)
    return new_class

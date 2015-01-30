#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#----------------------------------------------------------------------
# xotl.ql.core
#----------------------------------------------------------------------
# Copyright (c) 2012-2014 Merchise Autrement and Contributors
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
    '''Make a class support iteration like `this`:obj:.

    Example::

        @thesefy
        class Entity(object):
            pass

    Then, the following query is possible::

        query = (entity for entity in Entity)

    And it will be equivalent to::

        query = (entity for entity in (e for e in this if instance(e, Entity)))

    Other examples::

        Integers = thesefy(int)
        query = (i for i in Integers if i < 10)

    '''
    from xoutil import Unset

    class new_meta(type(target)):
        def __new__(cls, name, bases, attrs):
            from xoutil.iterators import dict_update_new
            baseattrs = {'__doc__': getattr(bases[0], '__doc__', ''),
                         '__module__': getattr(bases[0], '__module__', '')}
            dict_update_new(attrs, baseattrs)
            return super(new_meta, cls).__new__(cls, name, bases, attrs)

        def __iter__(self):
            from types import GeneratorType
            try:
                result = super(new_meta, self).__iter__()
            except AttributeError:
                result = Unset
            if isinstance(result, GeneratorType):
                return result
            elif result is Unset:
                return (obj for obj in this if isinstance(obj, target))
            else:
                raise TypeError('Class {target} has a metaclass with an '
                                '__iter__ that does not support thesefy'
                                .format(target=target))

    from xoutil.objects import metaclass

    class new_class(metaclass(new_meta), target):
        pass

    return new_class

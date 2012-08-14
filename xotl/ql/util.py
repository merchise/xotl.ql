#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#----------------------------------------------------------------------
# xotl.ql.util
#----------------------------------------------------------------------
# Copyright (c) 2012 Merchise Autrement
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under
# the terms of the LICENCE attached in the distribution package.
#
# Created on Aug 14, 2012


from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        unicode_literals as _py3_unicode,
                        absolute_import as _py3_abs_imports)


from xoutil.objects import get_first_of
from xoutil.context import context
from xoutil.proxy import UNPROXIFING_CONTEXT
from xoutil.decorators import assignment_operator

from xotl.ql.these import These

__docstring_format__ = 'rst'
__author__ = 'manu'



# XXX: Util types for bound/unbound and named/unnamed this instances.
# TODO: Check whether we need this or not.

class _complementof(type):
    def __instancecheck__(self, instance):
        return not isinstance(instance, self.target)


@assignment_operator(maybe_inline=False)
def complementof(name, typ, doc=None):
    return _complementof(name,
                         (object,),
                         {'target': typ,
                          '__doc__': doc})


class _bound_type(type):
    def __instancecheck__(self, instance):
        with context(UNPROXIFING_CONTEXT):
            return (isinstance(instance, These) and
                    getattr(instance, 'binding', False))


class bound(object):
    '''
    Pure type for bound `this` instances::

        >>> from xotl.ql import this
        >>> isinstance(this, bound)
        False

        >>> who = next(parent for parent in this if parent.age > 32)
        >>> isinstance(who, bound)
        True
    '''
    __metaclass__ = _bound_type


unbound = complementof(bound)


class _named_type(type):
    def __instancecheck__(self, instance):
        with context(UNPROXIFING_CONTEXT):
            return (isinstance(instance, These) and
                    get_first_of(instance, 'name', '__name__', default=False))


class named(object):
    '''
    Pure type for named this instances::

        >>> from xotl.ql import this
        >>> isinstance(this, named)
        False

        >>> isinstance(this('parent'), named)
        True
    '''
    __metaclass__ = _named_type


unnamed = complementof(named)

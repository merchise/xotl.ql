#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#----------------------------------------------------------------------
# xotl.ql.core
#----------------------------------------------------------------------
# Copyright (c) 2012 Merchise Autrement and Contributors
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License (GPL) as published by the Free
# Software Foundation; either version 3 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Created on May 24, 2012


'''Extends the :mod:`~xotl.ql.expressions` language to provide universal
accessors.

The :obj:`this` object stands for every object in the "universe" (e.g. the
index, the storage, etc.) :obj:`this` eases the construction of expressions
directly, and also provides a query language by means of Python's syntax for
:ref:`generator expressions <py:generator-expressions>` and list, and dict
comprehensions (we shall call them comprehensions).

'''

from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        unicode_literals as _py3_unicode,
                        absolute_import)

import re
from itertools import count

from xoutil.objects import get_first_of, validate_attrs
from xoutil.context import context
from xoutil.proxy import UNPROXIFING_CONTEXT, unboxed

from zope.component import getUtility
from zope.interface import implements, directlyProvides

from xotl.ql.expressions import _true, _false, ExpressionTree
from xotl.ql.expressions import UNARY, BINARY, N_ARITY
from xotl.ql.interfaces import (IThese, IQuery, IQueryPart, IExpressionTree,
                                IExpressionCapable, IQueryPartContainer,
                                IBoundThese, IQueryTranslator,
                                IQueryConfiguration)


__docstring_format__ = 'rst'
__author__ = 'manu'


__all__ = (b'this',)


class ResourceType(type):
    pass


# TODO: Think about this
class Resource(object):
    __slots__ = ('_name', '_parent')
    __metaclass__ = ResourceType

    _counter = count(1)
    valid_names_regex = re.compile(r'^(?!\d)\w[\d\w_]*$')

    def __init__(self, name, **kwargs):
        with context(UNPROXIFING_CONTEXT):
            self.validate_name(name)
            self._name = name
            self._parent = kwargs.get('parent', None)


    @classmethod
    def validate_name(cls, name):
        '''
        Checks names of named These instances::

            >>> this('::1nvalid')        # doctest: +ELLIPSIS
            Traceback (most recent call last):
                ...
            NameError: Invalid identifier '1nvalid' ...
        '''
        regexp = cls.valid_names_regex
        if context['_INVALID_THESE_NAME']:
            regexp = re.compile(r'::i\d+')
        if name and not regexp.match(name):
            raise NameError('Invalid identifier %r for a named These '
                            'instance' % name)


    @property
    def name(self):
        '''
        `These` instances may be named in order to be distiguishable from each
        other in a query where two instances may represent different objects.
        '''
        return getattr(self, '_name', None)


    @property
    def parent(self):
        '''
        `These` instances may have a parent `these` instance from which they
        are to be "drawn". If fact, only the pair of attributes ``(parent,
        name)`` allows to distiguish two instances from each other.
        '''
        return getattr(self, '_parent', None)


    @property
    def root_parent(self):
        '''
        The top-most parent of the instace or self if it has no parent.
        '''
        parent = getattr(self, 'parent', None)
        if parent is not None:
            return parent.root_parent
        else:
            return self


class These(Resource):
    '''
    The type of :obj:`this` symbol: an unnamed object that may placed in
    queries and whose interpretation may be dependant of the query context and
    the context in which `this` symbol is used in the query itself.
    '''
    implements(IThese)

    __slots__ = ('_binding')


    def __init__(self, name=None, **kwargs):
        with context(UNPROXIFING_CONTEXT):
            self.validate_name(name)
            self._name = name
            self._parent = kwargs.get('parent', None)
            self._binding = None
            if not self._parent:
                self.bind(get_first_of(kwargs, 'binding', 'filter',
                                       default=None))


    def bind(self, expression):
        self.binding = expression


    @property
    def binding(self):
        '''
        The expression to which the `These` instance is bound to or None.
        '''
        current, res = self, None
        while current and not res:
            res = getattr(current, '_binding', None)
            current = current.parent
        return res if res else None


    @binding.setter
    def binding(self, value):
        # This causes errors with objects that have __slots__, do we
        # really need slots, or do we really need IBoundThese
        #
        # if value is not None:
        #     directlyProvides(self, IBoundThese)
        parent = getattr(self, 'parent', None)
        if parent:
            parent.binding = value
        else:
            self._binding = value


    @binding.deleter
    def binding(self):
        parent = getattr(self, 'parent', None)
        if parent:
            del parent.binding
        else:
            del self._binding


    @classmethod
    def _newname(cls):
        return '::i{count}'.format(count=next(cls._counter))


    def __getattribute__(self, attr):
        # Notice we can't use the __getattr__ way because then things like::
        #   this.name and this.binding
        # would not work properly.
        get = super(These, self).__getattribute__
        if attr in ('__mro__', '__class__', '__doc__',) or context[UNPROXIFING_CONTEXT]:
            return get(attr)
        else:
            return These(name=attr, parent=self)


    def __call__(self, *args):
        with context(UNPROXIFING_CONTEXT):
            parent = self.parent
        if parent is not None:
            from .expressions import invoke
            return ExpressionTree(invoke, self, *args)
        else:
            raise TypeError()


    def __iter__(self):
        '''
        Yields a single instance of this but wrapped around an object that
        allows for conditions to be bound this instance::

            >>> tuple(parent.age for parent in this)  # doctest: +ELLIPSIS
            (<this('i...').age at 0x...>,)


        This allows an idiomatic way to express retrievals from several types
        of models::

            >>> fetch = next    # Just to show off the idiom
            >>> fetch((parent, child)   # doctest: +ELLIPSIS
            ...            for parent in this('parent')
            ...            for child in parent.children)
            (<this('parent') ...>, <this('parent').children ...>)


        Furthermore, if should be natural to introduce conditions over the
        results. But the support for this to happen cannot be realiably
        introduced in here::

            >>> fetch(parent for parent in this('parent')  # doctest: +ELLIPSIS
            ...        if parent.age > 32)
            <this('parent') ...>
        '''
        with context(UNPROXIFING_CONTEXT):
            name = self.name
            parent = self.parent
        if name:
            query = Query(instance=self)
            instance = QueryPart(instance=self, query=query)
            yield instance
        else:
            # We should generate a new-name
            with context(UNPROXIFING_CONTEXT), context('_INVALID_THESE_NAME'):
                instance = type(self)(self._newname(), parent=parent)
            yield next(iter(instance))

    def __str__(self):
        with context(UNPROXIFING_CONTEXT):
            name = self.name
            parent = self.parent
        if parent is None and not name:
            return 'this'
        elif parent is None and name:
            return "this('{name}')".format(name=name)
        elif parent is not None and name:
            return "{parent}.{name}".format(parent=str(parent), name=name)
        else:  # parent and not name:
            assert False


    def __repr__(self):
        return '<%s at 0x%x>' % (str(self), id(self))


    def __eq__(self, other):
        '''
            >>> with context(UNPROXIFING_CONTEXT):
            ...    this('parent') == this('parent')
            True

            >>> from xotl.ql.expressions import _true
            >>> (this('parent') == this('parent')) is _true
            True
        '''
        from xotl.ql.expressions import eq
        with context(UNPROXIFING_CONTEXT):
            if isinstance(other, These):
                res = validate_attrs(self, other, ('name', 'parent',
                                                   'binding'))
            else:
                res = False
        if context[UNPROXIFING_CONTEXT]:
            return res
        else:
            if not res:
                return eq(self, other)
            else:
                # In logic A == A is always true so we don't produce nothing
                # for it.
                return _true


    def __ne__(self, other):
        '''
            >>> with context(UNPROXIFING_CONTEXT):
            ...    this('parent') != this('parent')
            False

            >>> from xotl.ql.expressions import _false
            >>> (this('parent') != this('parent')) is _false
            True
        '''
        from xotl.ql.expressions import ne
        with context(UNPROXIFING_CONTEXT):
            if isinstance(other, These):
                res = validate_attrs(self, other, ('name', 'parent',
                                                   'binding'))
            else:
                res = False
        if context[UNPROXIFING_CONTEXT]:
            return not res
        else:
            if not res:
                return ne(self, other)
            else:
                return _false


    def __lt__(self, other):
        '''
            >>> this < 1     # doctest: +ELLIPSIS
            <expression 'this < 1' ...>
        '''
        from xotl.ql.expressions import lt
        return lt(self, other)


    def __gt__(self, other):
        '''
            >>> this > 1     # doctest: +ELLIPSIS
            <expression 'this > 1' ...>
        '''
        from xotl.ql.expressions import gt
        return gt(self, other)


    def __le__(self, other):
        '''
            >>> this <= 1     # doctest: +ELLIPSIS
            <expression 'this <= 1' ...>
        '''
        from xotl.ql.expressions import le
        return le(self, other)


    def __ge__(self, other):
        '''
            >>> this >= 1     # doctest: +ELLIPSIS
            <expression 'this >= 1' ...>
        '''
        from xotl.ql.expressions import ge
        return ge(self, other)


    def __and__(self, other):
        '''
            >>> this & 1     # doctest: +ELLIPSIS
            <expression 'this and 1' ...>
        '''
        from xotl.ql.expressions import and_
        return and_(self, other)


    def __rand__(self, other):
        '''
            >>> 1 & this     # doctest: +ELLIPSIS
            <expression '1 and this' ...>
        '''
        from xotl.ql.expressions import and_
        return and_(other, self)


    def __or__(self, other):
        '''
            >>> this | 1     # doctest: +ELLIPSIS
            <expression 'this or 1' ...>
        '''
        from xotl.ql.expressions import or_
        return or_(self, other)


    def __ror__(self, other):
        '''
            >>> 1 | this     # doctest: +ELLIPSIS
            <expression '1 or this' ...>
        '''
        from xotl.ql.expressions import or_
        return or_(other, self)


    def __xor__(self, other):
        '''
            >>> this ^ 1     # doctest: +ELLIPSIS
            <expression 'this xor 1' ...>
        '''
        from xotl.ql.expressions import xor_
        return xor_(self, other)


    def __rxor__(self, other):
        '''
            >>> 1 ^ this     # doctest: +ELLIPSIS
            <expression '1 xor this' ...>
        '''
        from xotl.ql.expressions import xor_
        return xor_(other, self)


    def __add__(self, other):
        '''
            >>> this + 1       # doctest: +ELLIPSIS
            <expression 'this + 1' ...>
        '''
        from xotl.ql.expressions import add
        return add(self, other)


    def __radd__(self, other):
        '''
            >>> 1 + this       # doctest: +ELLIPSIS
            <expression '1 + this' ...>
        '''
        from xotl.ql.expressions import add
        return add(other, self)


    def __sub__(self, other):
        '''
            >>> this - 1      # doctest: +ELLIPSIS
            <expression 'this - 1' ...>
        '''
        from xotl.ql.expressions import sub
        return sub(self, other)


    def __rsub__(self, other):
        '''
            >>> 1 - this      # doctest: +ELLIPSIS
            <expression '1 - this' ...>
        '''
        from xotl.ql.expressions import sub
        return sub(other, self)


    def __mul__(self, other):
        '''
            >>> this * 1    # doctest: +ELLIPSIS
            <expression 'this * 1' ...>
        '''
        from xotl.ql.expressions import mul
        return mul(self, other)


    def __rmul__(self, other):
        '''
            >>> 1 * this    # doctest: +ELLIPSIS
            <expression '1 * this' ...>
        '''
        from xotl.ql.expressions import mul
        return mul(other, self)


    def __div__(self, other):
        '''
            >>> this/1    # doctest: +ELLIPSIS
            <expression 'this / 1' ...>
        '''
        from xotl.ql.expressions import div
        return div(self, other)
    __truediv__ = __div__


    def __rdiv__(self, other):
        '''
            >>> 1 / this    # doctest: +ELLIPSIS
            <expression '1 / this' ...>
        '''
        from xotl.ql.expressions import div
        return div(other, self)
    __rtruediv__ = __rdiv__


    def __floordiv__(self, other):
        '''
            >>> this // 1    # doctest: +ELLIPSIS
            <expression 'this // 1' ...>
        '''
        from xotl.ql.expressions import floordiv
        return floordiv(self, other)


    def __rfloordiv__(self, other):
        '''
            >>> 1 // this    # doctest: +ELLIPSIS
            <expression '1 // this' ...>
        '''
        from xotl.ql.expressions import floordiv
        return floordiv(other, self)


    def __mod__(self, other):
        '''
            >>> this % 1    # doctest: +ELLIPSIS
            <expression 'this % 1' ...>
        '''
        from xotl.ql.expressions import mod
        return mod(self, other)


    def __rmod__(self, other):
        '''
            >>> 1 % this    # doctest: +ELLIPSIS
            <expression '1 % this' ...>
        '''
        from xotl.ql.expressions import mod
        return mod(other, self)


    def __pow__(self, other):
        '''
            >>> this**1    # doctest: +ELLIPSIS
            <expression 'this**1' ...>
        '''
        from xotl.ql.expressions import pow_
        return pow_(self, other)


    def __rpow__(self, other):
        '''
            >>> 1 ** this    # doctest: +ELLIPSIS
            <expression '1**this' ...>
        '''
        from xotl.ql.expressions import pow_
        return pow_(other, self)


    def __lshift__(self, other):
        '''
            >>> this << 1    # doctest: +ELLIPSIS
            <expression 'this << 1' ...>
        '''
        from xotl.ql.expressions import lshift
        return lshift(self, other)


    def __rlshift__(self, other):
        '''
            >>> 1 << this    # doctest: +ELLIPSIS
            <expression '1 << this' ...>
        '''
        from xotl.ql.expressions import lshift
        return lshift(other, self)


    def __rshift__(self, other):
        '''
            >>> this >> 1    # doctest: +ELLIPSIS
            <expression 'this >> 1' ...>
        '''
        from xotl.ql.expressions import rshift
        return rshift(self, other)


    def __rrshift__(self, other):
        '''
            >>> 1 >> this    # doctest: +ELLIPSIS
            <expression '1 >> this' ...>
        '''
        from xotl.ql.expressions import rshift
        return rshift(other, self)


    def __neg__(self):
        '''
            >>> -this         # doctest: +ELLIPSIS
            <expression '-this' ...>
        '''
        from xotl.ql.expressions import neg
        return neg(self)


    def __abs__(self):
        '''
            >>> abs(this)         # doctest: +ELLIPSIS
            <expression 'abs(this)' ...>
        '''
        from xotl.ql.expressions import abs_
        return abs_(self)


    def __pos__(self):
        '''
            >>> +this         # doctest: +ELLIPSIS
            <expression '+this' ...>
        '''
        from xotl.ql.expressions import pos
        return pos(self)


    def __invert__(self):
        '''
            >>> ~this         # doctest: +ELLIPSIS
            <expression '~this' ...>
        '''
        from xotl.ql.expressions import invert
        return invert(self)



class ThisClassType(ResourceType):
    pass



class ThisClass(These):
    '''
    The class for the :obj:`this` object.

    The `this` object is a singleton that behaves like any other
    :class:`These` instances but also allows the creation of named instances.

    '''
    __metaclass__ = ThisClassType


    def __call__(self, name, **kwargs):
        return These(name, **kwargs)


#: The `this` object is a unnamed universal "selector" that may be placed in
#: expressions and queries.
this = ThisClass()



def provides_any(which, *interfaces):
    with context(UNPROXIFING_CONTEXT):
        return any(interface.providedBy(which) for interface in interfaces)



def provides_all(which, *interfaces):
    with context(UNPROXIFING_CONTEXT):
        return all(interface.providedBy(which) for interface in interfaces)



class Query(object):
    implements(IQuery, IQueryPartContainer)

    __slots__ = ('instance', '_selection', '_filters',
                 '_ordering', '_partition', '_parts',
                 '_query_state')

    # TODO: Representation of grouping with dicts.
    def __init__(self, **kwargs):
        self.instance = instance = kwargs.get('instance')
        self.selection = kwargs.get('selection', instance)
        self.filters = kwargs.get('filters', None)
        self.ordering = kwargs.get('ordering', None)
        self.partition = kwargs.get('partition', None)
        self._parts = []


    @property
    def selection(self):
        return self._selection


    @selection.setter
    def selection(self, value):
        ok = lambda v: isinstance(v, (ExpressionTree, These))
        if ok(value):
            self._selection = (value, )
        elif isinstance(value, tuple) and all(ok(v) for v in value):
            self._selection = value
        # TODO: Include dict
        else:
            raise TypeError('The SELECT part of query should a valid '
                            'expression type, not %r' % value)

    @property
    def filters(self):
        return self._filters


    @filters.setter
    def filters(self, value):
        # TODO: Validate
        self._filters = value


    @property
    def ordering(self):
        return self._ordering

    @ordering.setter
    def ordering(self, value):
        from xotl.ql.expressions import pos, neg
        if value:
            ok = lambda v: (isinstance(v, ExpressionTree) and
                            value.op in (pos, neg))
            if ok(value):
                self._ordering = (value, )
            elif isinstance(value, tuple) and all(ok(v) for v in value):
                self._ordering = value
            else:
                raise TypeError('Expected a [tuple of] unary expressions; '
                                'got %r' % value)
        else:
            self._ordering = None

    @property
    def partition(self):
        return self._partition


    @partition.setter
    def partition(self, value):
        if not value or isinstance(value, slice):
            self._partition = value
        else:
            raise TypeError('Expected a slice; not a %r' % value)


    @property
    def offset(self):
        return self._partition.start


    @property
    def limit(self):
        return self._partition.stop


    def created_query_part(self, part):
        assert unboxed(part).query is self
        if isinstance(part, QueryPart):
            expression = unboxed(part).expression
            self._parts.append(expression)
        else:
            assert False


    def next(self):
        '''Support for retrieving objects directly from the query object. Of
        course this requires that an IQueryTranslator is configured.
        '''
        if not self._query_state:
            name = getUtility(IQueryConfiguration).query_translator_name
            translator = getUtility(IQueryTranslator,
                                    name if name else b'default')
            query_plan = translator.build_plan(self, order=self.ordering,
                                               partition=self.partition)
            self._query_state = query_plan()
        result, _state = next(self._query_state, (None, None))
        if result:
            self._query_state = _state
            return result
        else:
            self._query_state = None
            raise StopIteration


    def __iter__(self):
        'Creates a subquery'
        raise NotImplemented



class QueryPart(object):
    '''A class that wraps :class:`These` instances to build queries

    When iterating over this instance, this token is used to catch all
    expressions and build a :class:`Query` from it. This class is mostly
    internal and does not belongs to the Query Language API.

    '''
    implements(IQueryPart, )

    __slots__ = ('_query', '_expression')


    def __init__(self, **kwargs):
        with context(UNPROXIFING_CONTEXT):
            self._expression = get_first_of(kwargs,
                                            'instance',
                                            'expression',
                                            'binding')
            # TODO: assert that expression is ExpressionCapable
            self.query = kwargs.get('query')
            # TODO: assert self._query implements IQuery and
            #       IQueryPartContainer


    @property
    def query(self):
        return self._query


    @query.setter
    def query(self, value):
        if provides_any(value, IQuery):
            self._query = value
        else:
            raise TypeError('`query` attribute only accepts IQuery objects')


    @property
    def expression(self):
        return self._expression


    @expression.setter
    def expression(self, value):
        if provides_any(value, IExpressionCapable):
            self._expression = value
        else:
            raise TypeError('QueryParts wraps IExpressionCapable objects only')


    # TODO: Declare in which the interface?
    def __iter__(self):
        with context(UNPROXIFING_CONTEXT):
            return iter(self.instance)


    def __str__(self):
        with context(UNPROXIFING_CONTEXT):
            instance = self.expression
            query = self.query
            result = str(instance)
        return '<qp: %s; for %s>' % (result, query)
    __repr__ = __str__


    # TODO: In which interface?
    def __getattribute__(self, attr):
        get = super(QueryPart, self).__getattribute__
        if context[UNPROXIFING_CONTEXT]:
            return get(attr)
        else:
            with context(UNPROXIFING_CONTEXT):
                instance = get('expression')
                query = get('query')
            result = QueryPart(instance=getattr(instance, attr),
                               query=query)
            query.created_query_part(result)
            return result


    # TODO: Again, in which interface?
    def __call__(self, *args):
        with context(UNPROXIFING_CONTEXT):
            instance = self._instance
            query = self.query
        result = QueryPart(instance=instance(*args),
                           query=query)
        query.created_query_part(result)
        return result


    # This hooks into is_a expression to allow restricting queries to types
    # more easily.
    def _is_a(self, kind):
        if isinstance(kind, QueryPart):
            kind = unboxed(kind).expression
        with context(UNPROXIFING_CONTEXT):
            instance = self.expression
            query = self.query
            query.generator_kind = kind
        from xotl.ql.expressions import is_a
        return is_a(instance, kind)


    def __eq__(self, other):
        if isinstance(other, QueryPart):
            other = unboxed(other).expression
        with context(UNPROXIFING_CONTEXT):
            instance = self.expression
            query = self.query
        result = instance == other
        if provides_any(result, IExpressionTree, IThese):
            result = QueryPart(instance=result,
                               query=query)
            query.created_query_part(result)
        return result


    def __ne__(self, other):
        if isinstance(other, QueryPart):
            other = unboxed(other).expression
        with context(UNPROXIFING_CONTEXT):
            instance = self.expression
            query = self.query
        result = instance != other
        if provides_any(result, IExpressionTree, IThese):
            result = QueryPart(instance=result,
                               query=query)
            query.created_query_part(result)
        return result


    def __lt__(self, other):
        from operator import lt
        if isinstance(other, QueryPart):
            other = unboxed(other).expression
        with context(UNPROXIFING_CONTEXT):
            instance = self.expression
            query = self.query
        result = QueryPart(instance=lt(instance, other),
                           query=query)
        query.created_query_part(result)
        return result


    def __gt__(self, other):
        from operator import gt
        if isinstance(other, QueryPart):
            other = unboxed(other).expression
        with context(UNPROXIFING_CONTEXT):
            instance = self.expression
            query = self.query
        result = QueryPart(instance=gt(instance, other),
                           query=query)
        query.created_query_part(result)
        return result


    def __le__(self, other):
        from operator import le
        if isinstance(other, QueryPart):
            other = unboxed(other).expression
        with context(UNPROXIFING_CONTEXT):
            instance = self.expression
            query = self.query
        result = QueryPart(instance=le(instance, other),
                           query=query)
        query.created_query_part(result)
        return result


    def __ge__(self, other):
        from operator import ge
        if isinstance(other, QueryPart):
            other = unboxed(other).expression
        with context(UNPROXIFING_CONTEXT):
            instance = self.expression
            query = self.query
        result = QueryPart(instance=ge(instance, other),
                           query=query)
        query.created_query_part(result)
        return result


    def __and__(self, other):
        from operator import and_
        if isinstance(other, QueryPart):
            other = unboxed(other).expression
        with context(UNPROXIFING_CONTEXT):
            instance = self.expression
            query = self.query
        result = QueryPart(instance=and_(instance, other),
                           query=query)
        query.created_query_part(result)
        return result


    def __rand__(self, other):
        from operator import and_
        if isinstance(other, QueryPart):
            other = unboxed(other).expression
        with context(UNPROXIFING_CONTEXT):
            instance = self.expression
            query = self.query
        result = QueryPart(instance=and_(other, instance),
                           query=query)
        query.created_query_part(result)
        return result


    def __or__(self, other):
        from operator import or_
        if isinstance(other, QueryPart):
            other = unboxed(other).expression
        with context(UNPROXIFING_CONTEXT):
            instance = self.expression
            query = self.query
        result = QueryPart(instance=or_(instance, other),
                           query=query)
        query.created_query_part(result)
        return result


    def __ror__(self, other):
        from operator import or_
        if isinstance(other, QueryPart):
            other = unboxed(other).expression
        with context(UNPROXIFING_CONTEXT):
            instance = self.expression
            query = self.query
        result = QueryPart(instance=or_(other, instance),
                           query=query)
        query.created_query_part(result)
        return result



    def __xor__(self, other):
        from operator import xor
        if isinstance(other, QueryPart):
            other = unboxed(other).expression
        with context(UNPROXIFING_CONTEXT):
            instance = self.expression
            query = self.query
        result = QueryPart(instance=xor(instance, other),
                           query=query)
        query.created_query_part(result)
        return result



    def __rxor__(self, other):
        from operator import xor
        if isinstance(other, QueryPart):
            other = unboxed(other).expression
        with context(UNPROXIFING_CONTEXT):
            instance = self.expression
            query = self.query
        result = QueryPart(instance=xor(other, instance),
                           query=query)
        query.created_query_part(result)
        return result



    def __add__(self, other):
        from operator import add
        if isinstance(other, QueryPart):
            other = unboxed(other).expression
        with context(UNPROXIFING_CONTEXT):
            instance = self.expression
            query = self.query
        result = QueryPart(instance=add(instance, other),
                           query=query)
        query.created_query_part(result)
        return result



    def __radd__(self, other):
        from operator import add
        if isinstance(other, QueryPart):
            other = unboxed(other).expression
        with context(UNPROXIFING_CONTEXT):
            instance = self.expression
            query = self.query
        result = QueryPart(instance=add(other, instance),
                           query=query)
        query.created_query_part(result)
        return result



    def __sub__(self, other):
        from operator import sub
        if isinstance(other, QueryPart):
            other = unboxed(other).expression
        with context(UNPROXIFING_CONTEXT):
            instance = self.expression
            query = self.query
        result = QueryPart(instance=sub(instance, other),
                           query=query)
        query.created_query_part(result)
        return result



    def __rsub__(self, other):
        from operator import sub
        if isinstance(other, QueryPart):
            other = unboxed(other).expression
        with context(UNPROXIFING_CONTEXT):
            instance = self.expression
            query = self.query
        result = QueryPart(instance=sub(other, instance),
                           query=query)
        query.created_query_part(result)
        return result



    def __mul__(self, other):
        from operator import mul
        if isinstance(other, QueryPart):
            other = unboxed(other).expression
        with context(UNPROXIFING_CONTEXT):
            instance = self.expression
            query = self.query
        result = QueryPart(instance=mul(instance, other),
                           query=query)
        query.created_query_part(result)
        return result



    def __rmul__(self, other):
        from operator import mul
        if isinstance(other, QueryPart):
            other = unboxed(other).expression
        with context(UNPROXIFING_CONTEXT):
            instance = self.expression
            query = self.query
        result = QueryPart(instance=mul(other, instance),
                           query=query)
        query.created_query_part(result)
        return result



    def __div__(self, other):
        from operator import div
        if isinstance(other, QueryPart):
            other = unboxed(other).expression
        with context(UNPROXIFING_CONTEXT):
            instance = self.expression
            query = self.query
        result = QueryPart(instance=div(instance, other),
                           query=query)
        query.created_query_part(result)
        return result
    __truediv__ = __div__


    def __rdiv__(self, other):
        from operator import div
        if isinstance(other, QueryPart):
            other = unboxed(other).expression
        with context(UNPROXIFING_CONTEXT):
            instance = self.expression
            query = self.query
        result = QueryPart(instance=div(other, instance),
                           query=query)
        query.created_query_part(result)
        return result
    __rtruediv__ = __rdiv__


    def __floordiv__(self, other):
        from operator import floordiv
        if isinstance(other, QueryPart):
            other = unboxed(other).expression
        with context(UNPROXIFING_CONTEXT):
            instance = self.expression
            query = self.query
        result = QueryPart(instance=floordiv(instance, other),
                           query=query)
        query.created_query_part(result)
        return result


    def __rfloordiv__(self, other):
        from operator import floordiv
        if isinstance(other, QueryPart):
            other = unboxed(other).expression
        with context(UNPROXIFING_CONTEXT):
            instance = self.expression
            query = self.query
        result = QueryPart(instance=floordiv(other, instance),
                           query=query)
        query.created_query_part(result)
        return result


    def __mod__(self, other):
        from operator import mod
        if isinstance(other, QueryPart):
            other = unboxed(other).expression
        with context(UNPROXIFING_CONTEXT):
            instance = self.expression
            query = self.query
        result = QueryPart(instance=mod(instance, other),
                           query=query)
        query.created_query_part(result)
        return result


    def __rmod__(self, other):
        from operator import mod
        if isinstance(other, QueryPart):
            other = unboxed(other).expression
        with context(UNPROXIFING_CONTEXT):
            instance = self.expression
            query = self.query
        result = QueryPart(instance=mod(other, instance),
                           query=query)
        query.created_query_part(result)
        return result


    def __pow__(self, other):
        from operator import pow_
        if isinstance(other, QueryPart):
            other = unboxed(other).expression
        with context(UNPROXIFING_CONTEXT):
            instance = self.expression
            query = self.query
        result = QueryPart(instance=pow_(instance, other),
                           query=query)
        query.created_query_part(result)
        return result


    def __rpow__(self, other):
        from operator import pow_
        if isinstance(other, QueryPart):
            other = unboxed(other).expression
        with context(UNPROXIFING_CONTEXT):
            instance = self.expression
            query = self.query
        result = QueryPart(instance=pow_(other, instance),
                           query=query)
        query.created_query_part(result)
        return result


    def __lshift__(self, other):
        from operator import lshift
        if isinstance(other, QueryPart):
            other = unboxed(other).expression
        with context(UNPROXIFING_CONTEXT):
            instance = self.expression
            query = self.query
        result = QueryPart(instance=lshift(instance, other),
                           query=query)
        query.created_query_part(result)
        return result


    def __rlshift__(self, other):
        from operator import lshift
        if isinstance(other, QueryPart):
            other = unboxed(other).expression
        with context(UNPROXIFING_CONTEXT):
            instance = self.expression
            query = self.query
        result = QueryPart(instance=lshift(other, instance),
                           query=query)
        query.created_query_part(result)
        return result


    def __rshift__(self, other):
        from operator import rshift
        if isinstance(other, QueryPart):
            other = unboxed(other).expression
        with context(UNPROXIFING_CONTEXT):
            instance = self.expression
            query = self.query
        result = QueryPart(instance=rshift(instance, other),
                           query=query)
        query.created_query_part(result)
        return result


    def __rrshift__(self, other):
        from operator import rshift
        if isinstance(other, QueryPart):
            other = unboxed(other).expression
        with context(UNPROXIFING_CONTEXT):
            instance = self.expression
            query = self.query
        result = QueryPart(instance=rshift(other, instance),
                           query=query)
        query.created_query_part(result)
        return result


    def __neg__(self):
        with context(UNPROXIFING_CONTEXT):
            instance = self.expression
            query = self.query
        result = QueryPart(instance=-instance,
                           query=query)
        query.created_query_part(result)
        return result


    def __abs__(self):
        with context(UNPROXIFING_CONTEXT):
            instance = self.expression
            query = self.query
        result = QueryPart(instance=abs(instance),
                           query=query)
        query.created_query_part(result)
        return result


    def __pos__(self):
        with context(UNPROXIFING_CONTEXT):
            instance = self.expression
            query = self.query
        result = QueryPart(instance=+instance,
                           query=query)
        query.created_query_part(result)
        return result


    def __invert__(self):
        with context(UNPROXIFING_CONTEXT):
            instance = self.expression
            query = self.query
        result = QueryPart(instance=~instance,
                           query=query)
        query.created_query_part(result)
        return result


    def count(self):
        from xotl.ql.expressions import count as f_
        with context(UNPROXIFING_CONTEXT):
            who = getattr(self, 'binding', None) or self._instance
            result = f_(who)
            self._update_binding(result)
        return self


    def length(self):
        from xotl.ql.expressions import length as f_
        with context(UNPROXIFING_CONTEXT):
            who = getattr(self, 'binding', None) or self._instance
            result = f_(who)
            self._update_binding(result)
        return self


    def any_(self, other):
        from xotl.ql.expressions import any_ as f_
        with context(UNPROXIFING_CONTEXT):
            who = getattr(self, 'binding', None) or self._instance
            result = f_(who, other)
            self._update_binding(result)
        return self


    def all_(self, other):
        from xotl.ql.expressions import all_ as f_
        with context(UNPROXIFING_CONTEXT):
            who = getattr(self, 'binding', None) or self._instance
            result = f_(who, other)
            self._update_binding(result)
        return self


    def min_(self):
        from xotl.ql.expressions import min_ as f_
        with context(UNPROXIFING_CONTEXT):
            who = getattr(self, 'binding', None) or self._instance
            result = f_(who)
            self._update_binding(result)
        return self


    def max_(self):
        from xotl.ql.expressions import max_ as f_
        with context(UNPROXIFING_CONTEXT):
            who = getattr(self, 'binding', None) or self._instance
            result = f_(who)
            self._update_binding(result)
        return self


    def invoke(self, *args):
        from xotl.ql.expressions import invoke as f_
        with context(UNPROXIFING_CONTEXT):
            who = getattr(self, 'binding', None) or self._instance
            result = f_(who, *args)
            self._update_binding(result)
        return self


def these(comprehesion):
    '''
    Post-process the query comprehension to build a Query.
    '''
    import types
    assert isinstance(comprehesion, (types.GeneratorType, dict))
    if isinstance(comprehesion, types.GeneratorType):
        preselection = next(comprehesion)
        if not isinstance(preselection, tuple):
            preselection = (preselection, )
        for qp in preselection:
            with context(UNPROXIFING_CONTEXT):
                query = qp.query
                sel = qp.expression
            # TODO: search for these instances inside expression
            print(qp, sel, query)
            parts = query._parts
            if sel is parts[-1]:
                parts.pop(-1)
            query.filters = parts.pop(-1) if parts else None
        return query



#def thesefy(target):
#    '''
#    Takes in a class and injects it an `__iter__` method that can be used
#    to form queries::
#
#        >>> @thesefy
#        ... class Person(object):
#        ...    pass
#
#        >>> from xoutil.proxy import unboxed
#        >>> from xotl.ql.expressions import q
#        >>> q = these(who for who in Person if who.age > 30)
#        >>> unboxed(q).binding    # doctest: +ELLIPSIS
#        <expression '(is_a(this('...'), <class '...Person'>)) and (this('...').age > 30)' ...>
#
#    This is only usefull if your real class does not have a metaclass of its
#    own that do that.
#    '''
#    from xoutil.objects import nameof
#    class new_meta(type(target)):
#        def __new__(cls, name, bases, attrs):
#            return super(new_meta, cls).__new__(cls, nameof(target), bases, attrs)
#        def __iter__(self):
#            from xotl.ql.expressions import is_a
#            return iter(these(s for s in this if is_a(s, self)))
#    class new_class(target):
#        __metaclass__ = new_meta
#    return new_class

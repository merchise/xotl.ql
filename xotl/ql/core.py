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
from functools import partial

from xoutil.types import Unset
from xoutil.objects import validate_attrs
from xoutil.context import context
from xoutil.proxy import UNPROXIFING_CONTEXT, unboxed
from xoutil.decorators import decorator
from xoutil.aop.basic import complementor

from zope.component import getUtility
from zope.interface import implementer

from xotl.ql.expressions import _true, _false, ExpressionTree, OperatorType
from xotl.ql.expressions import UNARY, BINARY, N_ARITY
from xotl.ql.interfaces import (IThese, IGeneratorToken, IQueryPart, IExpressionTree,
                                IExpressionCapable, IQueryPartContainer,
                                IQueryTranslator, IQueryConfiguration,
                                IQueryObject)


__docstring_format__ = 'rst'
__author__ = 'manu'


__all__ = (b'this',)


class ExpressionError(Exception):
    '''Base class for expressions related errors'''



class ResourceType(type):
    pass



# TODO: Think about this name.
# TODO: Do we really need the __slots__ stuff? We must stress the inmutability
#       of some structures, but __slots__ does not enforce inmutability,
#       just disables the __dict__ in objects.
class Resource(object):
    __slots__ = ('_name', '_parent')
    __metaclass__ = ResourceType

    _counter = count(1)
    valid_names_regex = re.compile(r'^(?!\d)\w[\d\w_]*$')

    def __init__(self, name=None, **kwargs):
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
            NameError: Invalid identifier '::1nvalid' ...
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

@implementer(IThese)
class These(Resource):
    '''
    The type of the :obj:`this` symbol: an unnamed object that may placed in
    queries and whose interpretation depends on the query context and the
    context in which `this` symbol is used inside the query itself.
    '''

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
            from xotl.ql.expressions import invoke
            return ExpressionTree(invoke, self, *args)
        else:
            raise TypeError()


    def __iter__(self):
        '''
        Yields a single instance of :class:`query part
        <xotl.ql.interfaces.IQueryPart>` that wraps `self`.

        This allows an idiomatic way to express queries::

            >>> parent, child = next((parent, child)
            ...                            for parent in this('parent')
            ...                            for child in parent.children)
            >>> (parent, child)    # doctest: +ELLIPSIS
            (<...this('parent')...>, <...this('parent').children...>)

        A `token` object is attached to each part::

            >>> unboxed(parent).token        # doctest: +ELLIPSIS
            <...GeneratorToken object at 0x...>

        The attached `token` object is different for each part if those parts
        are generated from different generators token (see
        :class:`~xotl.ql.interfaces.IGeneratorToken`).

            >>> unboxed(parent).token is not unboxed(child).token
            True

        However, in a query with a single generator token (only one `for`), the
        `token` object is shared::

            >>> parent, children = next((parent, parent.children)
            ...                            for parent in this('parent'))
            >>> unboxed(parent).token is unboxed(children).token
            True

        .. warning::

           We have used `next` here directly over the comprehensions, but the
           query language **does not** support this kind of construction.

           Queries must be built by calling the :func:`these` passing the
           comprehesion as its first argument.
        '''
        with context(UNPROXIFING_CONTEXT):
            name = self.name
            parent = self.parent
        if name:
            token = GeneratorToken(expression=self)
            instance = QueryPart(expression=self, token=token)
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
                res = validate_attrs(self, other, ('name', 'parent'))
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
                res = validate_attrs(self, other, ('name', 'parent'))
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
            <expression 'this mod 1' ...>
        '''
        from xotl.ql.expressions import mod
        return mod(self, other)


    def __rmod__(self, other):
        '''
            >>> 1 % this    # doctest: +ELLIPSIS
            <expression '1 mod this' ...>
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
            <expression 'not this' ...>
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


    def __init__(self, *args, **kwargs):
        super(ThisClass, self).__init__(*args, **kwargs)
        self.__doc__ = ('The `this` object is a unnamed universal '
                          '"selector" that may be placed in expressions and '
                          'queries')


    def __call__(self, name, **kwargs):
        return These(name, **kwargs)


    def __repr__(self):
        # XXX: Hack to avoid sphinx writing <this at 0x...> in the docs.
        # XXX: However, it's useful to have this repr when debugging.
        import sys
        sphinxed = 'sphinx' in sys.argv[0] if sys.argv else False
        return None if sphinxed else super(ThisClass, self).__repr__()



#: The `this` object is a unnamed universal "selector" that may be placed in
#: expressions and queries.
this = ThisClass()



def provides_any(which, *interfaces):
    with context(UNPROXIFING_CONTEXT):
        return any(interface.providedBy(which) for interface in interfaces)



def provides_all(which, *interfaces):
    with context(UNPROXIFING_CONTEXT):
        return all(interface.providedBy(which) for interface in interfaces)




class _QueryObjectType(type):
    def these(self, comprehesion, **kwargs):
        '''Builds a :term:`query object` from a :term:`query expression` given
        by a comprehesion.

        :param comprehension: The :term:`query expression` to be processed.

        :param ordering: The ordering expressions.
        :type ordering: A tuple of ordering expressions.

        :param partition: A slice `(offset, limit, step)` that represents the
                          part of the result set to be retrieved.

                          You may express this by individually providing the
                          arguments `offset`, `limit` and `step`.

                          If you provide the `partition` argument, those will
                          be ignored (and a warning will be logged).

        :type partition: slice or None

        :param offset: Indivually express the offset of the `partition` param.
        :type offset: int or None

        :param limit: Indivually express the limit of the `partition` param.
        :type limit: int or None

        :param step: Indivually express the step of the `partition` param.
        :type step: int or None

        :returns: An :class:`~xotl.ql.interfaces.IQueryObject` instance that
                  represents the QueryObject expressed by the `comprehension`
                  and the `kwargs`.

        :rtype: :class:`QueryObject`

        '''
        from types import GeneratorType
        assert isinstance(comprehesion, GeneratorType)
        selected_parts = next(comprehesion)
        with context(UNPROXIFING_CONTEXT):
            if not isinstance(selected_parts, (list, tuple)):
                selected_parts = (selected_parts, )
            selected_parts = tuple(reversed(selected_parts))
            selection = []
            tokens = []
            filters = []
            for part in selected_parts:
                expr = part.expression
                selection.append(expr)
                token = part.token
                tokens.append(token.expression)
                previous_parts = token._parts
                if previous_parts and previous_parts[-1] is expr:
                    previous_parts.pop(-1)
                filters.extend(part for part in previous_parts
                                    if part not in filters)
            query = self()
            query.selection = tuple(reversed(selection))
            query.tokens = tuple(set(tokens))
            query.filters = tuple(set(filters))
            query.ordering = kwargs.get('ordering', None)
            partition = kwargs.get('partition', None)
            offset = kwargs.get('offset', None)
            limit = kwargs.get('limit', None)
            step = kwargs.get('step', None)
            if not partition and (offset or limit or step):
                partition = slice(offset, limit, step)
            elif partition and (offset or limit or step):
                import warnings
                warnings.warn('Ignoring offset, limit and/or step argument '
                              'since partition was passed', stacklevel=2)
            query.partition = partition
            return query


    def __call__(self, *args, **kwargs):
        if args:
            from xoutil.types import GeneratorType
            first_arg, args = args[0], args[1:]
            if not args:
                if isinstance(first_arg, GeneratorType):
                    return self.these(first_arg, **kwargs)
                # TODO: Other types of queries

        result = super(self, self).__new__(self)
        result.__init__(*args, **kwargs)
        return result


@implementer(IQueryObject)
class QueryObject(object):
    '''
    Represents a query. See :class:`xotl.ql.interfaces.IQueryObject`.
    '''
    __metaclass__ = _QueryObjectType


    def __init__(self):
        self._selection = None
        self.tokens = None
        self._filters = None
        self._ordering = None
        self.partition = None


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
                raise TypeError('Expected a [tuple of] unary (+ or -) '
                                'expressions; got %r' % value)
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
            raise TypeError('Expected a slice or None; got %r' % value)


    @property
    def offset(self):
        return self._partition.start


    @property
    def limit(self):
        return self._partition.stop


    @property
    def step(self):
        return self._partition.step


    def next(self):
        '''Support for retrieving objects directly from the query object. Of
        course this requires that an IQueryTranslator is configured.
        '''
        state = getattr(self, '_query_state', Unset)
        if state is Unset:
            # TODO: This will change, configuration vs deployment.
            #       How to inject translator into a global/local context?
            name = getUtility(IQueryConfiguration).query_translator_name
            translator = getUtility(IQueryTranslator,
                                    name if name else b'default')
            query_plan = translator.build_plan(self)
            state = self._query_state = query_plan()
        result, state = next(state, (Unset, state))
        if result is not Unset:
            self._query_state = state
            return result
        else:
            delattr(self, '_query_state')
            raise StopIteration


    def __iter__(self):
        'Creates a subquery'
        raise NotImplementedError


these = QueryObject


@implementer(IGeneratorToken, IQueryPartContainer)
class GeneratorToken(object):
    '''
    Represents a token in the syntactical tree that is used as generator.

    This object is also an :class:`~xotl.ql.interfaces.IQueryPartContainer`,
    because in this implementation we need to record each time an
    :class:`~xotl.ql.interfaces.IQueryPart` is created in order to later
    retrieve the filters related to this generator token.

    '''
    __slots__ = ('_expression', '_parts')


    # TODO: Representation of grouping with dicts.
    def __init__(self, expression):
        assert provides_any(expression, IThese)
        self._expression = expression
        self._parts = []


    def __eq__(self, other):
        with context(UNPROXIFING_CONTEXT):
            if isinstance(other, GeneratorToken):
                return self._expression == other._expression


    @property
    def expression(self):
        return self._expression


    @staticmethod
    def mergable(parts, expression):
        assert context[UNPROXIFING_CONTEXT]
        top = parts[-1]
        if top is expression:
            return True
        elif IExpressionTree.providedBy(expression):
            result = any(child is top for child in expression.children)
            if not result and IExpressionTree.providedBy(top):
                return any(child is expression for child in top.children)
            else:
                return result
        elif IThese.providedBy(expression):
            return expression.parent is top
        else:
            raise TypeError('Parts should be either these instance or '
                            'expression trees; not %s' % type(expression))


    def created_query_part(self, part):
        with context(UNPROXIFING_CONTEXT):
            if provides_all(part, IQueryPart):
                expression = part.expression
                parts = self._parts
                if parts:
                    while parts and self.mergable(parts, expression):
                        parts.pop()
                self._parts.append(expression)
            else:
                assert False



def _build_unary_operator(operation):
    method_name = operation._method_name
    def method(self):
        with context(UNPROXIFING_CONTEXT):
            instance = self.expression
            token = self.token
        result = QueryPart(expression=operation(instance),
                           token=token)
        token.created_query_part(result)
        return result
    method.__name__ = method_name
    return method



def _build_binary_operator(operation, inverse=False):
    if not inverse:
        method_name = operation._method_name
    else:
        method_name = operation._rmethod_name
    if method_name:
        def method(self, other):
            with context(UNPROXIFING_CONTEXT):
                instance = self.expression
                token = self.token
                tokens = getattr(self, 'tokens', [token])
                if isinstance(other, QueryPart):
                    other_token = other.token
                    other_tokens = getattr(other, 'tokens', [other_token])
                    other = other.expression
                else:
                    other_token = None
                    other_tokens = []
                tokens.extend(t for t in other_tokens if t not in tokens)
            if not inverse:
                result = QueryPart(expression=operation(instance, other),
                                   token=token)
            else:
                result = QueryPart(expression=operation(other, instance),
                                   token=token)
            result.tokens = tokens
            for token in tokens:
                token.created_query_part(result)
            return result
        method.__name__ = method_name
        return method



_part_operations = {operation._method_name:
                    _build_unary_operator(operation)
                 for operation in OperatorType.operators
                    if getattr(operation, 'arity', None) == UNARY}
_part_operations.update({operation._method_name:
                        _build_binary_operator(operation)
                      for operation in OperatorType.operators
                        if getattr(operation, 'arity', None) is BINARY})

_part_operations.update({operation._rmethod_name:
                        _build_binary_operator(operation, True)
                      for operation in OperatorType.operators
                        if getattr(operation, 'arity', None) is BINARY and
                           getattr(operation, '_rmethod_name', None)})


QueryPartOperations = type(b'QueryPartOperations', (object,), _part_operations)


@implementer(IQueryPart)
@complementor(QueryPartOperations)
class QueryPart(object):
    '''A class that wraps either :class:`These` or :class:`ExpressionTree` that
    implements the :class:`xotl.ql.interfaces.IQueryPart` interface.

    To build a query object from a comprehension like in::

        these(count(parent.children) for parent in this if parent.age > 34)

    We need to differiante the IF (``parent.age > 34``) part of the
    comprehension from the SELECTION (``count(parent.children)``); which in the
    general case are both expressions. The following procedure is a sketch of
    what happens to accomplish that:

    1. Python creates a generator object, and invokes the :func:`these`
       function with the generator as it's sole argument.

    2. The :func:`these` function invokes `next` upon the generator object.

    3. Python invokes ``iter(this)`` which constructs internally another
       instance of :class:`These` but with a unique name, and delegates the
       ``iter`` to this instance.

    4. The newly created named These instance creates :class:`GeneratorToken`
       and assign itself to the
       :attr:`~xotl.ql.interfaces.IGeneratorToken.token` attribute.

       A :class:`QueryPart` is created; the GeneratorToken instance is assigned
       to the attribute :attr:`~xotl.ql.interfaces.IQueryPart.token`, and
       `self` is assigned to the attribute
       :attr:`~xotl.ql.interfaces.IQueryPart.expression`.

       The query part is yielded to the calling :func:`these`.

    5. Python now processes the `if` part of the comprehension.

       - First, ``parent.age`` is processed. The query part's
         `__getattribute__` method is invoked, which delegates the call to it's
         :attr:`~IQueryPart.expression` attribute. Since, it is an
         :class:`These` instance, it returns another named These instance.

         A new query part is created with `expression` set to the result, the
         :attr:`~IQueryPart.token` is inherited from the current query part.

         Upon creation of this new query part, the token's
         :meth:`~xotl.ql.interfaces.IQueryPartContainer.created_query_part` is
         called with the newly created query part as its argument.

         The token maintains a stack of created parts. Whenever a new query
         part is created it pushes it on top of the stack, if the new query
         part *is not derived from the part on the top* of the stack, otherwise
         it just replaces the top with the new one. (In fact, it removes all
         parts from the top of the stack that are somehow contained in the
         newly created part.)

       - Next, Python invokes the method `__gt__` for the newly created query
         part which, in turn, delegates the call to its :attr:`expression`
         attribute.

         The result is again wrapped inside another query part and it's token's
         ``created_query_part`` is invoked. Since the resultant expression is
         derived from the previously created part, the token only maintains the
         last created part in its stack.

    6. Now Python starts to process the "selection" part of the Query, but we
       don't know that since there's no signal from the language that indicates
       such an event.

       It processes the `parent.children` by calling the `__getattribute__` of
       the query part, as before this call is delegated and the result is
       wrapped with another query part.

       When calling the `created_query_part` method, the token realizes that
       ``parent.children`` is not derived from ``parent.age > 34``, so it
       pushes the new part into the stack instead of replacing the top.

       Now the `count(...)` expression is invoked, and using the
       :class:`xotl.ql.expressions.FunctorOperator` protocol the `_count`
       method of the returned query part is invoked. Again, this is delegated
       to the wrapped expression and a new :class:`ExpressionTree` is created
       and wrapped inside a new query part.

       Once more, the `created_query_part` method is invoked, and this time it
       replaces the ``parent.children`` on the top of the stack for
       ``count(parent.children)``.

    7. Now the control is returned to the :func:`these` function and `next`
       returns a `QueryPart` whose `expression` is equivalent to
       ``count(parent.children)``.

    8. The QueryPart's `token` attribute is inspected to retrieve any previous
       *filter expressions* from the parts stack (disregarding the top-most if
       it's the same as the selection.)

    9. The :func:`these` creates a new :class:`QueryObject` object and extracts the
       `expression` from the selected query part and assigns it to the
       :attr:`~xotl.ql.interfaces.IQueryObject.selection` attribute of the query
       object, any retrieved expressions from the parts stack of the tokens are
       appended to the :attr:`~xotl.ql.interfaces.IQueryObject.filters` attribute.

    10. For the query above the query object returned will have its arguments
        with following values:

        selection
          ``(count(parent.children), )``

        filters
          ``[parent.age > 34]``

        Actually the ``parent`` will be something like ``this('::i1387')``.

    '''
    __slots__ = ('_token', '_expression', '_tokens')


    def __init__(self, **kwargs):
        with context(UNPROXIFING_CONTEXT):
            self._expression = kwargs.get('expression')
            # TODO: assert that expression is ExpressionCapable
            self._token = None
            self.token = token = kwargs.get('token')
            self._tokens = [token]
            # TODO: assert self._query implements IGeneratorToken and
            #       IQueryPartContainer


    @property
    def token(self):
        return self._token


    @token.setter
    def token(self, value):
        if not self._token and provides_any(value, IGeneratorToken):
            self._token = value
        else:
            raise TypeError('`query` attribute only accepts IGeneratorToken objects')


    @property
    def tokens(self):
        return list(self._tokens)


    @tokens.setter
    def tokens(self, value):
        from xoutil.types import is_collection
        with context(UNPROXIFING_CONTEXT):
            tokens = self._tokens
            if is_collection(value):
                assert all(provides_any(g, IGeneratorToken) for g in value)
                tokens.extend(token for token in value if token not in tokens)
            else:
                assert provides_any(value, IGeneratorToken)
                tokens.append(value)


    @property
    def expression(self):
        return self._expression


    @expression.setter
    def expression(self, value):
        if provides_any(value, IExpressionCapable):
            self._expression = value
        else:
            raise TypeError('QueryParts wraps IExpressionCapable objects only')


    def __iter__(self):
        with context(UNPROXIFING_CONTEXT):
            expression = self.expression
            # This kind of a hack: since in queries like::
            #     ((parent, child) for parent in this
            #                      for child in parent.children)
            # The `parent.children` will generate a part and push it to the
            # query; but this part should be there; so we need to remove it
            #
            # Review note: Maybe we could this part but wrapped inside an
            # `iter` mark to easy the detection of subqueries that are not
            # in the selection.
            if IThese.providedBy(expression):
                parts = self.token._parts
                if parts and parts[-1] is expression:
                    parts.pop(-1)
            return iter(expression)


    def __str__(self):
        with context(UNPROXIFING_CONTEXT):
            instance = self.expression
            token = self.token
            result = str(instance)
        return '<qp: %s; for %s>' % (result, token)
    __repr__ = __str__


    # TODO: In which interface?
    def __getattribute__(self, attr):
        get = super(QueryPart, self).__getattribute__
        if context[UNPROXIFING_CONTEXT]:
            return get(attr)
        else:
            with context(UNPROXIFING_CONTEXT):
                instance = get('expression')
                token = get('token')
            result = QueryPart(expression=getattr(instance, attr),
                               token=token)
            token.created_query_part(result)
            return result


    # TODO: Again, in which interface?
    def __call__(self, *args):
        with context(UNPROXIFING_CONTEXT):
            instance = self.expression
            token = self.token
        result = QueryPart(expression=instance(*args),
                           token=token)
        token.created_query_part(result)
        return result


    def any_(self, *args):
        from xotl.ql.expressions import any_ as f
        with context(UNPROXIFING_CONTEXT):
            instance = self.expression
            token = self.token
        result = QueryPart(expression=f(instance, *args),
                           token=token)
        token.created_query_part(result)
        return result


    def all_(self, *args):
        from xotl.ql.expressions import all_ as f
        with context(UNPROXIFING_CONTEXT):
            instance = self.expression
            token = self.token
        result = QueryPart(expression=f(instance, *args),
                           token=token)
        token.created_query_part(result)
        return result


    def min_(self, *args):
        from xotl.ql.expressions import min_ as f
        with context(UNPROXIFING_CONTEXT):
            instance = self.expression
            token = self.token
        result = QueryPart(expression=f(instance, *args),
                           token=token)
        token.created_query_part(result)
        return result


    def max_(self, *args):
        from xotl.ql.expressions import max_ as f
        with context(UNPROXIFING_CONTEXT):
            instance = self.expression
            token = self.token
        result = QueryPart(expression=f(instance, *args),
                           token=token)
        token.created_query_part(result)
        return result


    def invoke(self, *args):
        from xotl.ql.expressions import invoke as f
        with context(UNPROXIFING_CONTEXT):
            instance = self.expression
            token = self.token
        result = QueryPart(expression=f(instance, *args),
                           token=token)
        token.created_query_part(result)
        return result



@decorator
def thesefy(target, name=None):
    '''
    Takes in a class and injects it an `__iter__` so that the class may take
    part of `this` in :term:`query expressions <query expression>`.

        >>> @thesefy
        ... class Entity(object):
        ...    def __init__(self, **kwargs):
        ...        for k, v in kwargs.items():
        ...            setattr(self, k, v)
        >>> q = these(which for which in Entity if which.name.startswith('A'))

    The previous query is rougly equivalent to::

        >>> from xotl.ql.expressions import is_instance
        >>> q2 = these(which for which in this
        ...                if is_instance(which, Entity)
        ...                if which.name.startswith('A'))

    You may test, that an `in_instance(..., Entity)` expression is in the query
    object filters::

        >>> any(unboxed(filter).operation is not is_instance
        ...     or filter.children[1] is Entity for filter in q.filters)
        True

    This is only useful if your real class does not have a metaclass of its own
    that do that. However, if you do have a metaclass with an `__iter__` method
    it should either return an `IQueryPart` instance or a `generator object`.

    Optionally (usually for debugging purposes only) you may pass a name to
    the decorator that will be used as the name for the internally generated
    :class:`These` instance.

        >>> @thesefy('Entity')
        ... class Entity(object):
        ...    pass

        >>> q = these(which for which in Entity if which.name.startswith('A'))
        >>> q.selection        # doctest: +ELLIPSIS
        (<this('Entity') at 0x...>,)

    This way it's easier to doc-test::

        >>> filters = q.filters
        >>> expected_is = is_instance(this('Entity'), Entity)
        >>> expected_filter = this('Entity').name.startswith('A')

        >>> any(unboxed(expected_is) == f for f in filters)
        True

        >>> any(unboxed(expected_filter) == f for f in filters)
        True
    '''
    from xoutil.objects import nameof
    class new_meta(type(target)):
        def __new__(cls, name, bases, attrs):
            return super(new_meta, cls).__new__(cls, nameof(target), bases, attrs)
        def __iter__(self):
            from types import GeneratorType
            from xotl.ql.interfaces import IQueryPart
            try:
                result = super(new_meta, self).__iter__()
            except AttributeError:
                result = Unset
            if isinstance(result, GeneratorType):
                return result
            elif result is not Unset and IQueryPart.providedBy(result):
                return iter((result, ))
            elif result is Unset:
                from xotl.ql.expressions import is_instance
                query_part = next(iter(this(name)))
                is_instance(query_part, self)
                return iter((query_part, ))
            else:
                raise TypeError('Class {target} has a metaclass with an '
                                '__iter__ that does not support thesefy'.format(target=target))

    class new_class(target):
        __metaclass__ = new_meta
    new_class.__doc__ = getattr(target, '__doc__', None)
    return new_class

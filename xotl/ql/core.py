#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#----------------------------------------------------------------------
# xotl.ql.core
#----------------------------------------------------------------------
# Copyright (c) 2012 Merchise Autrement and Contributors
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under
# the terms of the LICENCE attached in the distribution package.
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

import threading

from xoutil.types import Unset
from xoutil.objects import validate_attrs
from xoutil.context import context
from xoutil.proxy import UNPROXIFING_CONTEXT
from xoutil.decorators import decorator
from xoutil.aop.basic import complementor

from zope.component import getUtility
from zope.interface import implementer
from zope.interface import alsoProvides, noLongerProvides

from xotl.ql.expressions import _true, _false, ExpressionTree, OperatorType
from xotl.ql.expressions import UNARY, BINARY, N_ARITY
from xotl.ql.interfaces import (ITerm,
                                IBoundTerm,
                                IGeneratorToken,
                                IQueryPart,
                                IExpressionTree,
                                IExpressionCapable,
                                IQueryTranslator,
                                IQueryConfiguration,
                                IQueryObject,
                                IQueryParticlesBubble)


__docstring_format__ = 'rst'
__author__ = 'manu'


__all__ = (b'this', b'these',)


# A thread-local namespace to avoid using context. Just to test if this
# avoid the context's bug.
_local = threading.local()


def _get_bubbles_stack():
    unset = object()
    stack = getattr(_local, 'bubbles', unset)
    if stack is unset:
        stack = _local.bubbles = []
    return stack


def _create_and_push_bubble():
    'Creates a bubble and pushes it to the local stack'
    bubbles = _get_bubbles_stack()
    bubble = QueryParticlesBubble()
    bubbles.append(bubble)
    return bubble


def _pop_bubble():
    'Removes the top-most bubble from the bubble stack'
    bubbles = _get_bubbles_stack()
    return bubbles.pop(-1)


def _get_current_bubble():
    'Returns the top-most bubble'
    bubbles = _get_bubbles_stack()
    return bubbles[-1]


def _emit_part(part):
    'Emits a particle to the current bubble'
    bubble = _get_current_bubble()
    bubble.capture_part(part)


def _emit_token(token):
    'Emits a token to the current bubble'
    bubble = _get_current_bubble()
    bubble.capture_token(token)


@implementer(ITerm)
class Term(object):
    '''
    The type of the :obj:`this` symbol: an unnamed object that may placed in
    queries and whose interpretation depends on the query context and the
    context in which `this` symbol is used inside the query itself.
    '''

    _counter = count(1)
    valid_names_regex = re.compile(r'^(?!\d)\w[\d\w_]*$')

    def __init__(self, name=None, **kwargs):
        with context(UNPROXIFING_CONTEXT):
            self.validate_name(name)
            self._name = name
            self._parent = kwargs.get('parent', None)
            binding = kwargs.get('binding', None)
            if binding:
                self.binding = binding

    @classmethod
    def validate_name(cls, name):
        '''
        Checks names of named Term instances::

            >>> this('::1nvalid')        # doctest: +ELLIPSIS
            Traceback (most recent call last):
                ...
            NameError: Invalid identifier '::1nvalid' ...
        '''
        regexp = cls.valid_names_regex
        if context['_INVALID_THESE_NAME']:
            regexp = re.compile(r'::i\d+')
        if name and not regexp.match(name):
            raise NameError('Invalid identifier %r for a named Term '
                            'instance' % name)

    @property
    def name(self):
        '''
        `Term` instances may be named in order to be distinguishable from each
        other in a query where two instances may represent different objects.
        '''
        return getattr(self, '_name', None)

    @property
    def parent(self):
        '''
        `Term` instances may have a parent `these` instance from which they
        are to be "drawn". If fact, only the pair of attributes ``(parent,
        name)`` allows to distinguish two instances from each other.
        '''
        return getattr(self, '_parent', None)

    @property
    def root_parent(self):
        '''
        The top-most parent of the instance or self if it has no parent.
        '''
        parent = getattr(self, 'parent', None)
        if parent is not None:
            return parent.root_parent
        else:
            return self

    @property
    def binding(self):
        result = getattr(self, '_proper_binding', None)
        parent = self.parent
        while not result and parent:
            result = getattr(parent, 'binding', None)
            parent = parent.parent
        return result

    @binding.setter
    def binding(self, value):
        if value:
            alsoProvides(self, IBoundTerm)
        else:
            noLongerProvides(self, IBoundTerm)
        self._proper_binding = value

    @classmethod
    def _newname(cls):
        return '::i{count}'.format(count=next(cls._counter))

    def __getattribute__(self, attr):
        # Notice we can't use the __getattr__ way because then things like
        # ``this.name`` would not work properly.
        get = super(Term, self).__getattribute__
        if (attr in ('__mro__', '__class__', '__doc__',) or
            context[UNPROXIFING_CONTEXT]):
            return get(attr)
        else:
            return Term(name=attr, parent=self)

    def __call__(self, *args, **kwargs):
        with context(UNPROXIFING_CONTEXT):
            parent = self.parent
        if parent is not None:
            from xotl.ql.expressions import invoke
            return ExpressionTree(invoke, self, *args, **kwargs)
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

        .. warning::

           We have used `next` here directly over the comprehensions, but the
           query language **does not** support this kind of construction.

           Queries must be built by calling the :func:`these` passing the
           comprehension as its first argument.
        '''
        with context(UNPROXIFING_CONTEXT):
            name = self.name
            parent = self.parent
        with context(UNPROXIFING_CONTEXT):
            if name:
                token = GeneratorToken(expression=self)
                bound_term = Term(name, parent=parent, binding=token)
            else:
                # When iterating an instance without a name (i.e the `this`
                # object), we should generate a new name (of those simple
                # mortals can't use)
                with context('_INVALID_THESE_NAME'):
                    name = self._newname()
                    term = Term(name, parent=parent)
                    token = GeneratorToken(expression=term)
                    bound_term = Term(name, parent=parent, binding=token)
        instance = QueryPart(expression=bound_term)
        _emit_token(token)
        yield instance

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
            if isinstance(other, Term):
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
            if isinstance(other, Term):
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


class ThisClass(Term):
    '''
    The class for the :obj:`this` object.

    The `this` object is a singleton that behaves like any other :class:`Term`
    instances but also allows the creation of named instances.

    '''

    def __init__(self, *args, **kwargs):
        super(ThisClass, self).__init__(*args, **kwargs)
        self.__doc__ = ('The `this` object is a unnamed universal '
                          '"selector" that may be placed in expressions and '
                          'queries')

    def __call__(self, name, **kwargs):
        return Term(name, **kwargs)

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


@implementer(IQueryParticlesBubble)
class QueryParticlesBubble(object):
    def __init__(self):
        self._particles = []
        self._parts = []
        self._tokens = []

    @property
    def parts(self):
        return self._parts[:]

    @property
    def tokens(self):
        return self._tokens[:]

    @property
    def particles(self):
        return self._particles[:]

    def mergable(self, expression):
        'Returns true if `expression` is mergeable with the last captured part'
        from xoutil.compat import itervalues_
        assert context[UNPROXIFING_CONTEXT]
        is_expression = IExpressionTree.providedBy
        top = self._parts[-1]
        if top is expression:
            return True
        elif is_expression(expression):
            result = any(child is top for child in expression.children)
            if not result:
                return any(child is top
                           for child in itervalues_(expression.named_children))
            else:
                return result
        elif ITerm.providedBy(expression):
            return expression.parent is top
        else:
            raise TypeError('Parts should be either these instance or '
                            'expression trees; not %s' % type(expression))

    def capture_part(self, part):
        '''Captures an emitted query part.

        When a given part is captured, it might replace the lastly previously
        emitted parts if either of the following conditions hold:

        - The capture part *is* the same last emitted part.

        - The captured part is a term, and the last emitted part *is* its
          parent, then the parent part is replaced by the newly captured part.

        - The captured part is an expression and the last emitted part *is* one
          of its children (named or positional).

        The previous conditions are cycled while any of them hold against the
        particle at the "end" of the :attr:`particles` collection.

        Note that in an expression like ``invoke(some, a > b, b > c,
        argument=(c > d))`` before the whole expression is formed (and thus the
        part that represents it is captured), all of the arguments emitted
        particles, so we should remove those contained parts and just keep the
        bigger one that has them all.

        .. note::

           Checks **are** done with the `is` operator and not with `==`. Doing
           otherwise may lead to undesired results::

               these(parent.name for parent in this if parent.name)

           If `==` would be used, then the filter part `parent.name` would be
           lost.

        :param part: The emitted query part
        :type part: :class:`IQueryPart`
        '''
        with context(UNPROXIFING_CONTEXT):
            if provides_all(part, IQueryPart):
                expression = part.expression
                parts = self._parts
                if parts:
                    mergable = self.mergable
                    while parts and mergable(expression):
                        top = parts.pop()
                        self._particles.remove(top)
                parts.append(expression)
                self._particles.append(expression)
            else:
                assert False

    def capture_token(self, token):
        '''Captures an emitted token.

        When a token is emitted if the last previously created part is a term
        that *is* the same as the :attr:`IGeneratorToken.expression`, then this
        last term should be removed from the particles collection.

        This is because in a query like::

            these((parent, child)
                  for parent in this
                  for child in parent.children)

        The `parent.children` emits itself as a query part and immediately it
        is transformed to a token.

        :param token: The emitted token
        :type token: :class:`IGeneratorToken`
        '''
        tokens = self._tokens
        with context(UNPROXIFING_CONTEXT):
            assert IGeneratorToken.providedBy(token)
            parts = self._parts
            if parts:
                top = parts.pop(-1)
                if token.expression is not top:
                    parts.append(top)
        if token not in tokens:
            tokens.append(token)
            self._particles.append(token)


class _QueryObjectType(type):
    def these(self, comprehension, **kwargs):
        '''Builds a :term:`query object` from a :term:`query expression` given
        by a comprehension.

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

        :param offset: Individually express the offset of the `partition`
                       parameter.

        :type offset: int or None

        :param limit: Individually express the limit of the `partition`
                      parameter.

        :type limit: int or None

        :param step: Individually express the step of the `partition`
                     parameter.

        :type step: int or None

        :returns: An :class:`~xotl.ql.interfaces.IQueryObject` instance that
                  represents the QueryObject expressed by the `comprehension`
                  and the `kwargs`.

        :rtype: :class:`QueryObject`


        .. note::

           All others keyword arguments are copied to the
           :attr:`~xotl.ql.interface.IQueryObject.params` attribute, so that
           :term:`query translators <query translator>` may use them.

        '''
        from types import GeneratorType
        assert isinstance(comprehension, GeneratorType)
        bubble = _create_and_push_bubble()
        try:
            selected_parts = next(comprehension)
        finally:
            b = _pop_bubble()
            assert b is bubble
        with context(UNPROXIFING_CONTEXT):
            if not isinstance(selected_parts, (list, tuple)):
                selected_parts = (selected_parts,)
            selected_parts = tuple(reversed(selected_parts))
            selection = []
            tokens = bubble.tokens
            filters = bubble.parts
            for part in selected_parts:
                expr = part.expression
                if filters and expr is filters[-1]:
                    filters.pop(-1)
                selection.append(expr)
            query = self()
            query.selection = tuple(reversed(selection))
            query.tokens = tuple(set(token.expression for token in tokens))
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
            query.params = {k: v for k, v in kwargs.items()
                            if k not in ('partition', 'offset',
                                         'limit', 'step')}
            return query

    def __call__(self, *args, **kwargs):
        if args:
            from types import GeneratorType
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
        self.params = {}

    @property
    def selection(self):
        return self._selection

    @selection.setter
    def selection(self, value):
        ok = lambda v: isinstance(v, (ExpressionTree, Term))
        if ok(value):
            self._selection = (value,)
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
                self._ordering = (value,)
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
            conf = getUtility(IQueryConfiguration)
            name = getattr(conf, 'default_translator_name', None)
            translator = getUtility(IQueryTranslator,
                                    name if name else b'default')
            query_plan = translator.build_plan(self)
            state = self._query_state = query_plan()
        result = next(state, (Unset, Unset))
        if isinstance(result, tuple):
            result, state = result
        else:
            state = Unset
        if result is not Unset:
            if state:
                self._query_state = state
            return result
        else:
            delattr(self, '_query_state')
            raise StopIteration

    def __iter__(self):
        'Creates a subquery'
        raise NotImplementedError


these = QueryObject


@implementer(IGeneratorToken)
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
        assert provides_any(expression, ITerm)
        self._expression = expression
        self._parts = []

    def __eq__(self, other):
        with context(UNPROXIFING_CONTEXT):
            if isinstance(other, GeneratorToken):
                return self._expression == other._expression

    def __repr__(self):
        return '<tk: %r>' % self._expression

    @property
    def expression(self):
        return self._expression


def _query_part_method(target):
    '''Decorator of every method in QueryPart that emits its result to
    the "active" particle bubble.'''
    def inner(self, *args, **kwargs):
        result = target(self, *args, **kwargs)
        _emit_part(result)
        return result
    inner.__name__ = target.__name__
    return inner


def _build_unary_operator(operation):
    method_name = operation._method_name
    def method(self):
        result = QueryPart(expression=operation(self))
        return result
    method.__name__ = method_name
    return _query_part_method(method)


def _build_binary_operator(operation, inverse=False):
    if not inverse:
        method_name = operation._method_name
    else:
        method_name = operation._rmethod_name
    if method_name:
        def method(self, *others):
            if not inverse:
                result = QueryPart(expression=operation(self, *others))
            else:
                assert operation._arity == BINARY
                other = others[0]
                result = QueryPart(expression=operation(other, self))
            return result
        method.__name__ = method_name
        return _query_part_method(method)


_part_operations = {operation._method_name:
                    _build_unary_operator(operation)
                 for operation in OperatorType.operators
                    if getattr(operation, 'arity', None) is UNARY}
_part_operations.update({operation._method_name:
                        _build_binary_operator(operation)
                      for operation in OperatorType.operators
                        if getattr(operation, 'arity', None) in (BINARY, N_ARITY)})

_part_operations.update({operation._rmethod_name:
                        _build_binary_operator(operation, True)
                      for operation in OperatorType.operators
                        if getattr(operation, 'arity', None) is BINARY and
                           getattr(operation, '_rmethod_name', None)})


QueryPartOperations = type(b'QueryPartOperations', (object,), _part_operations)


class _QueryPartType(type):
    def _target_(self, part):
        from xoutil.proxy import unboxed
        return unboxed(part).expression


@implementer(IQueryPart, ITerm)
@complementor(QueryPartOperations)
class QueryPart(object):
    '''A class that wraps either :class:`Term` or :class:`ExpressionTree` that
    implements the :class:`xotl.ql.interfaces.IQueryPart` interface.

    To build a query object from a comprehension like in::

        these(count(parent.children) for parent in this if parent.age > 34)

    We need to differentiate the IF (``parent.age > 34``) part of the
    comprehension from the SELECTION (``count(parent.children)``); which in the
    general case are both expressions.

    '''
    __metaclass__ = _QueryPartType
    __slots__ = ('_expression')

    def __init__(self, **kwargs):
        with context(UNPROXIFING_CONTEXT):
            self._expression = expression = kwargs.get('expression')
            assert IExpressionCapable.providedBy(expression)

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
            # XXX: In cases of sub-queries the part will be emitted, but the
            #      iter will be hold, so the token won't be emitted and the
            #      part won't be removed. So we're bringing this check back.
            bubble = _get_current_bubble()
            assert bubble
            if bubble._parts and expression is bubble._parts[-1]:
                bubble._parts.pop(-1)
            return iter(expression)

    def __str__(self):
        with context(UNPROXIFING_CONTEXT):
            instance = self.expression
            result = str(instance)
        return '<qp: %s>' % result
    __repr__ = __str__

    def __getattribute__(self, attr):
        get = super(QueryPart, self).__getattribute__
        if context[UNPROXIFING_CONTEXT]:
            return get(attr)
        else:
            with context(UNPROXIFING_CONTEXT):
                instance = get('expression')
            result = QueryPart(expression=getattr(instance, attr))
            _emit_part(result)
            return result

    @_query_part_method
    def __call__(self, *args, **kwargs):
        with context(UNPROXIFING_CONTEXT):
            instance = self.expression
        result = QueryPart(expression=instance(*args, **kwargs))
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

    The previous query is roughly equivalent to::

        >>> from xotl.ql.expressions import is_instance
        >>> q2 = these(which for which in this
        ...                if is_instance(which, Entity)
        ...                if which.name.startswith('A'))

    This is only useful if your real class does not have a metaclass of its own
    that do that. However, if you do have a metaclass with an `__iter__` method
    it should either return an `IQueryPart` instance or a `generator object`.

    Optionally (usually for debugging purposes only) you may pass a name to
    the decorator that will be used as the name for the internally generated
    :class:`Term` instance.

        >>> @thesefy('Entity')
        ... class Entity(object):
        ...    pass

        >>> q = these(which for which in Entity if which.name.startswith('A'))
        >>> q.selection        # doctest: +ELLIPSIS
        (<this('Entity') at 0x...>,)

    This way it's easier to create tests::

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
            return super(new_meta, cls).__new__(cls, nameof(target),
                                                bases, attrs)
        def __iter__(self):
            from types import GeneratorType
            try:
                result = super(new_meta, self).__iter__()
            except AttributeError:
                result = Unset
            if isinstance(result, GeneratorType):
                for item in result:
                    yield item
            elif result is not Unset and IQueryPart.providedBy(result):
                    yield result
            elif result is Unset:
                from xotl.ql.expressions import is_instance
                query_part = next(iter(this(name)))
                is_instance(query_part, self)
                yield query_part
            else:
                raise TypeError('Class {target} has a metaclass with an '
                                '__iter__ that does not support thesefy'
                                .format(target=target))

    class new_class(target):
        __metaclass__ = new_meta
    new_class.__doc__ = getattr(target, '__doc__', None)
    return new_class

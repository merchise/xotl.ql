#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#----------------------------------------------------------------------
# xotl.ql.translation.py
#----------------------------------------------------------------------
# Copyright (c) 2013 Merchise Autrement and Contributors
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under
# the terms of the LICENCE attached in the distribution package.
#
# Created on 2013-04-03

from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        unicode_literals as _py3_unicode,
                        absolute_import as _py3_abs_imports)

from xoutil.context import context
from xoutil.proxy import UNPROXIFING_CONTEXT
from xoutil.modules import modulemethod
from xoutil.types import Unset
from xoutil.decorator import memoized_property
from xoutil.compat import iteritems_

from xotl.ql.core import Term, GeneratorToken
from xotl.ql.expressions import _false, _true
from xotl.ql.expressions import OperatorType
from xotl.ql.expressions import ExpressionTree
from xotl.ql.expressions import UNARY, BINARY

from xotl.ql.expressions import EqualityOperator
from xotl.ql.expressions import NotEqualOperator
from xotl.ql.expressions import LogicalAndOperator
from xotl.ql.expressions import LogicalOrOperator
from xotl.ql.expressions import LogicalXorOperator
from xotl.ql.expressions import LogicalNotOperator
from xotl.ql.expressions import AdditionOperator
from xotl.ql.expressions import SubstractionOperator
from xotl.ql.expressions import DivisionOperator
from xotl.ql.expressions import MultiplicationOperator
from xotl.ql.expressions import FloorDivOperator
from xotl.ql.expressions import ModOperator
from xotl.ql.expressions import PowOperator
from xotl.ql.expressions import LeftShiftOperator
from xotl.ql.expressions import RightShiftOperator
from xotl.ql.expressions import LesserThanOperator
from xotl.ql.expressions import LesserOrEqualThanOperator
from xotl.ql.expressions import GreaterThanOperator
from xotl.ql.expressions import GreaterOrEqualThanOperator
from xotl.ql.expressions import ContainsExpressionOperator
from xotl.ql.expressions import IsInstanceOperator
from xotl.ql.expressions import LengthFunction
from xotl.ql.expressions import CountFunction
from xotl.ql.expressions import PositiveUnaryOperator
from xotl.ql.expressions import NegativeUnaryOperator
from xotl.ql.expressions import AbsoluteValueUnaryFunction
from xotl.ql.expressions import InvokeFunction
from xotl.ql.expressions import NewObjectFunction
from xotl.ql.expressions import AverageFunction
from xotl.ql.expressions import EndsWithOperator
from xotl.ql.expressions import StartsWithOperator
from xotl.ql.expressions import MinFunction
from xotl.ql.expressions import MaxFunction
from xotl.ql.expressions import AllFunction
from xotl.ql.expressions import AnyFunction

from xotl.ql.interfaces import IQueryTranslator

__author__ = "Manuel Vázquez Acosta <mva.led@gmail.com>"
__date__   = "Wed Apr  3 21:22:18 2013"


_avoid_modules = ('xotl.ql.*',
                  'xoutil.*',
                  'py.*',

                  # The name of the builtins module is different in Pythons
                  # versions.
                  type(1).__module__)


def defined(who, modules):
    '''Checks if `who` (or its class) is defined in any of the given
    `modules`.

    The `modules` sequence may contains elements *ending* in ".*" to signify a
    package.

    '''
    with context(UNPROXIFING_CONTEXT):
        try:
            mod = who.__module__
        except AttributeError:
            mod = type(who).__module__
    def check(target):
        if target.endswith('.*'):
            return mod.startswith(target[:-2])
        else:
            return mod == target
    return any(check(target) for target in modules)


def _iter_classes(accept=None, use_ignores=False):
    '''Iterates over all the classes currently in Python's VM memory
    for which `accept(cls)` returns True.

    If use_ignores is True classes and objects of types defined in xotl.ql's
    modules and builtins will be also ignored.

    '''
    import gc
    if use_ignores:
        filterby = lambda x: x.__module__ not in _avoid_modules and (not accept or accept(x))
    else:
        filterby = accept
    return (ob for ob in gc.get_objects()
                if isinstance(ob, type) and (not filterby or filterby(ob)))


# Real signature is _filter_by_pkg(*pkg_names, negate=False)
def _filter_by_pkg(*pkg_names, **kwargs):
    '''Returns an `accept` filter for _iter_classes/_iter_objects that only
    accepts classes/objects defined in pkg_names.

    '''
    negate = kwargs.get('negate', False)
    def accept(cls):
        result = defined(cls, pkg_names)
        return result if not negate else not result
    return accept


def _iter_objects(accept=None, use_ignores=False):
    '''Iterates over all objects currently in Python's VM memory for which
    ``accept(ob)`` returns True.

    '''
    import gc
    if use_ignores:
        filterby = lambda x: type(x).__module__ not in _avoid_modules and (not accept or accept(x))
    else:
        filterby = accept
    return (ob for ob in gc.get_objects()
                if not isinstance(ob, type) and (not filterby or filterby(ob)))


def get_term_vm_path(term):
    '''Gets the root and the "path" of a term in the VM.

    The root is actually the token to which this term is bound to.

    The path is a list of identifiers which are traversal steps from the
    root. For instance::

          these(child for parent in this
                      if parent.children & (parent.age > 33)
                      for child in parent.children
                      if child.age < 5)

    The term `child.age` in the last filter is actually encoded by the names:
    parent, children, age; but since this term is bound to `parent.children`,
    only `age` is part of the path.

    '''
    with context(UNPROXIFING_CONTEXT):
        token = term.binding
        root = token.expression
        res = []
        current = term
        while current and current is not root:
            res.insert(0, current.name)
            current = current.parent
        return (token, res)


def _build_unary_operator(operation):
    import operator
    method_name = operation._method_name
    if method_name.startswith('__'):
        real_operation = getattr(operator, method_name[2:-2], None)
    else:
        real_operation = getattr(operator, method_name, None)
    if real_operation:
        def method(self):
            return real_operation(self._get_current_value(default=_false))
        method.__name__ = method_name
        return method
    else:
        import warnings
        warnings.warn('Skipping %s' % method_name)

def _build_binary_operator(operation):
    import operator
    method_name = operation._method_name
    if method_name.startswith('__'):
        key = method_name[2:-2]
        if key in ('and', 'or'):
            key += '_'
        real_operation = getattr(operator, key, None)
    else:
        real_operation = getattr(operator, method_name, None)
    if real_operation:
        def method(self, other):
            value = self._get_current_value(default=_false)
            if isinstance(other, var):
                other = other._get_current_value(default=_false)
            return real_operation(value, other)
        method.__name__ = method_name
        return method
    else:
        import warnings
        warnings.warn('Skipping %s' % method_name)


def _build_rbinary_operator(operation):
    import operator
    method_name = getattr(operation, '_method_name', None)
    if method_name:
        if method_name.startswith('__'):
            key = method_name[2:-2]
            if key in ('and', 'or'):
                key += '_'
            real_operation = getattr(operator, key)
        else:
            real_operation = getattr(operator, method_name)
        def method(self, other):
            value = self._get_current_value(default=_false)
            if isinstance(other, var):
                other = other._get_current_value(default=_false)
            return real_operation(value, other)
        method.__name__ = getattr(operation, '_rmethod_name')
        return method
    else:
        import warnings
        warnings.warn('Skipping %s for %s' % (method_name,
                                              getattr(operation,
                                                      '_rmethod_name')))


_expr_operations = {operation._method_name: _build_unary_operator(operation)
                    for operation in OperatorType.operators
                    if getattr(operation, 'arity', None) == UNARY}
_expr_operations.update({operation._method_name:
                        _build_binary_operator(operation)
                      for operation in OperatorType.operators
                        if getattr(operation, 'arity', None) is BINARY})
_expr_operations.update({operation._rmethod_name:
                        _build_rbinary_operator(operation)
                      for operation in OperatorType.operators
                        if getattr(operation, 'arity', None) is BINARY and
                           getattr(operation, '_rmethod_name', None)})

_var = type(str('_var'), (object,), _expr_operations)
class var(_var):
    '''Represents a variable in the VM's memory.

    This basically implements the mapping between a syntatical ITerm and its
    current value in the VM.

    When a filter like ``parent.age < 32`` is translated it will be translated
    to something like ``var(parent.age, VM).__lt__(32)``. So the main job of
    `var` is to provide an object that behaves like the one in the VM.

    '''
    def __init__(self, term, vm):
        self.term = term
        self.vm = vm

    def _get_current_value(self, override=None, default=Unset):
        '''Gets the current value in the VM.'''
        vm = override or self.vm
        term = self.term
        root, path = get_term_vm_path(term)
        current = vm.get(root, Unset)
        step = None
        while current is not Unset and path:
            step = path.pop(0)
            current = getattr(current, step, Unset)
        if current is Unset:
            if path:
                raise AttributeError(step or root)
            elif default is not Unset:
                return default
            else:
                # XXX: We return _false if the path was completely consumed,
                # i.e: the failure point is the last attribute. I (manu) think
                # is less astonishing to return a falsy value than to fail. Of
                # course this works only for truth-testing; for traversing, a
                # _false token should yield nothing.
                return _false
        else:
            return current

    def __and__(self, other):
        value = self._get_current_value(default=_false)
        if value is _false:
            return _false
        if isinstance(other, var):
            other = other._get_current_value(default=_false)
        return bool(value) and bool(other)

    def __or__(self, other):
        value = self._get_current_value(default=_false)
        if value is _true:
            return _true
        if isinstance(other, var):
            other = other._get_current_value(default=_false)
        return bool(value) or bool(other)

    def _contains_(self, what):
        value = self._get_current_value()
        if isinstance(what, var):
            what = what._get_current_value()
        return what in value

    def __len__(self):
        value = self._get_current_value()
        return len(value)

    def _is_a(self, what):
        value = self._get_current_value()
        if isinstance(what, var):
            what = what._get_current_value()
        return isinstance(value, what)

    def startswith(self, preffix):
        value = self._get_current_value()
        if isinstance(preffix, var):
            preffix = preffix._get_current_value()
        return value.startswith(preffix)

    def endswith(self, suffix):
        value = self._get_current_value()
        if isinstance(suffix, var):
            suffix = suffix._get_current_value()
        return value.startswith(suffix)

    def __call__(self, *args, **kwargs):
        value = self._get_current_value()
        extract = lambda x: x._get_current_value() if isinstance(x, var) else x
        _args = (extract(a) for a in args)
        _kwargs = {k: extract(v) for k, v in kwargs.items()}
        return value(*_args, **_kwargs)

    def __bool__(self):
        value = self._get_current_value()
        return bool(value)
    __nonzero__ = __bool__


    # TODO: all_, any_, min_, max_,
    # @classmethod
    # def possible_subquery(cls, func, self, *args):
    #     first, rest = args[0], args[1:]
    #     extract = lambda x: x._get_current_value() if isinstance(x, var) else x
    #     _args = (extract(a) for a in args)
    #     if rest:
    #         return func(*_args)
    #     else:
    #         # TODO:
    #         return func(iter(first))


class _object(object):
    '''The type for objects build by ``new(object, ...)``.'''
    def __init__(self, **kwargs):
        for k, v in iteritems_(kwargs):
            setattr(self, k, v)


def new(t, **kwargs):
    '''The implementation of the `new` function operation.'''
    if t == object:
        return _object(**kwargs)
    else:
        return t(**kwargs)


vminstr_table = {}
class vminstr(object):
    '''Represents an instruction tree ready to be executed in the VM current
    state.

    This is used for both evaluating filters and selections.

    '''
    class vmcodeset(object):
        table = vminstr_table

        def codefor(operation):
            def decorator(func):
                assert operation not in vminstr_table
                vminstr_table[operation] = func
                return func
            return decorator

        @codefor(NewObjectFunction)
        def new_object(self, t, **kwargs):
            if isinstance(t, type):
                return new(**{arg: value() for arg, value in iteritems_(kwargs)})
            else:
                raise TypeError('The first argument to new should be a type. Not %s' % t)

        def sub_query_method(func):
            def inner(self, *args):
                from types import GeneratorType
                from xotl.ql.core import these
                query, rest = args[0], args[1:]
                if rest:
                    return func(args)
                if isinstance(query, GeneratorType):
                    query = these(query)
                plan = naive_translation(query, vm=dict(self.vm))
                return func(result for result in plan())
            return inner

        # all_ = codefor(AllFunction)(sub_query_method(all))
        # any_ = codefor(AnyFunction)(sub_query_method(any))
        # min_ = codefor(MinFunction)(sub_query_method(min))
        # max_ = codefor(MaxFunction)(sub_query_method(max))
        # sum_ = codefor(SumFunction)(sub_query_method(sum))

        def avg(vals):
            _sum, count = 0, 0
            for x in vals:
                _sum += x
                count += 1
            return _sum/count

        average = codefor(AverageFunction)(sub_query_method(avg))

        @codefor(LogicalAndOperator)
        def and_(self, x, y):
            if isinstance(x, var):
                x = x._get_current_value(default=False)
            elif callable(x):
                x = x()
            else:
                assert False
            if not bool(x):
                return False
            if isinstance(y, var):
                y = y._get_current_value(default=False)
            elif callable(y):
                y = y()
            else:
                assert False
            if bool(y):
                return True
            return False

        @codefor(LogicalOrOperator)
        def or_(self, x, y):
            if isinstance(x, var):
                x = x._get_current_value(default=False)
            elif callable(x):
                x = x()
            else:
                assert False
            if bool(x):
                return True
            if isinstance(y, var):
                y = y._get_current_value(default=False)
            elif callable(y):
                y = y()
            else:
                assert False
            if bool(y):
                return True
            return False

        @codefor(LogicalXorOperator)
        def xor_(self, x, y):
            return self.or_(x, y) and not self.and_(x, y)


        @codefor(LogicalNotOperator)
        def not_(self, x):
            if isinstance(x, var):
                x = x._get_current_value(default=False)
            elif callable(x):
                x = x()
            else:
                assert False
            return not bool(x)

        table.update({
            EqualityOperator: lambda self, x, y: x == y,
            NotEqualOperator: lambda self, x, y: x != y,
            AdditionOperator: lambda self, x, y: x + y,
            SubstractionOperator: lambda self, x, y: x - y,
            DivisionOperator: lambda self, x, y: x/y,
            MultiplicationOperator: lambda self, x, y: x*y,
            FloorDivOperator: lambda self, x, y: x//y,
            ModOperator: lambda self, x, y: x % y,
            PowOperator: lambda self, x, y: x**y,
            LeftShiftOperator: lambda self, x, y: x << y,
            RightShiftOperator: lambda self, x, y: x >> y,
            LesserThanOperator: lambda self, x, y: x < y,
            LesserOrEqualThanOperator: lambda self, x, y: x <= y,
            GreaterThanOperator: lambda self, x, y: x > y,
            GreaterOrEqualThanOperator: lambda self, x, y: x >= y,
            ContainsExpressionOperator: lambda self, x, y: y in x,
            IsInstanceOperator: lambda self, x, y: x._is_a(y),
            LengthFunction: lambda self, x: len(x),
            CountFunction: lambda self, x: len(x),
            PositiveUnaryOperator: lambda self, x: +x,
            NegativeUnaryOperator: lambda self, x: -x,
            AbsoluteValueUnaryFunction: lambda self, x: abs(x),
            InvokeFunction: lambda self, m, *a, **kw: m(*a, **kw)
        })


    def __init__(self, filter, vm):
        self.filter = filter
        self.vm = vm
        self._tree = None

    @memoized_property
    def tree(self):
        def e(node):
            if isinstance(node, Term):
                return var(node, self.vm)
            if isinstance(node, ExpressionTree):
                _args = tuple(e(x) for x in node.children)
                _kwargs = {k: e(v) for k, v in iteritems_(node.named_children)}
                assert node.operation in self.vmcodeset.table, 'I don\'t know how to translate %r' % node.operation
                return lambda: self.vmcodeset.table[node.operation](self, *_args, **_kwargs)
            return node # assumed to be as is
        return e(self.filter)

    def __call__(self, pre=None, post=None):
        tree = self.tree
        if isinstance(tree, var):
            return tree
        else:
            return tree()

    def chain(self, source):
        for ob in source:
            res = self()
            if bool(res):
                yield


class vmtoken(object):
    def __init__(self, token, vm, only=None):
        self.token = token
        self.vm = vm
        self.only = only

    def _getsource(self):
        only = self.only
        token = self.token
        term = token.expression
        with context(UNPROXIFING_CONTEXT):
            parent = term.parent
        use_ignores = True
        if only:
            from xoutil.compat import str_base
            if isinstance(only, str_base):
                only = (only, )
            accept = _filter_by_pkg(*only)
        else:
            accept = None
        if not parent:
            source =_iter_objects(accept=accept, use_ignores=use_ignores)
        else:
            # The term here probably a.b.c is bound to itself, so we must
            # create a var with the binding changed to the parent binding.
            with context(UNPROXIFING_CONTEXT):
                parent = term.parent
                binding = parent.binding
                term = term.clone(binding=binding)
            tk = var(term, self.vm)
            source = (ob for ob in tk._get_current_value(default=[]))
        return source

    def __iter__(self):
        vm = self.vm
        token = self.token
        for ob in self._getsource():
            vm[token] = ob
            yield

    def chain(self, previous):
        for inst in previous:
            for own in iter(self):
                yield


def naive_translation(query, **kwargs):
    '''Does a naive translation to Python's VM memory.
    '''
    import functools
    from xotl.ql import translation as trans

    only = kwargs.get('only', None)

    def mix(filters, tokens):
        '''Intertwines tokens and filters.'''
        if not filters:
            return tokens
        return list(sorted(tokens + filters,
                           key=functools.cmp_to_key(trans.cmp)))

    sorted_parts = mix(query.filters, query.tokens)
    assert isinstance(sorted_parts[0], GeneratorToken), sorted_parts

    def select(sel, vm):
        from xotl.ql.expressions import _false
        result = []
        selectors = (sel, ) if not isinstance(sel, tuple) else sel
        for s in selectors:
            if isinstance(s, Term):
                result.append(var(s, vm)._get_current_value())
            else:
                result.append(vminstr(s, vm)())
        if any(res is _false for res in result):
            return _false
        if isinstance(sel, tuple):
            return tuple(result)
        else:
            assert len(result) == 1
            return result[0]

    def plan(**plan_kwargs):
        # The algorithm is simple; first we "intertwine" tokens and filters
        # using a (stable) partial order: a filter comes before a token if and
        # only if neither of it's terms is bound to the token.
        #
        # The we just build several chained generators that either produce
        # (affect the vm) or filter.
        #
        from xotl.ql.expressions import _false
        parts = list(sorted_parts[:])
        vm = plan_kwargs.get('vm', None) or kwargs.get('vm', None) or {}
        result = vmtoken(parts.pop(0), vm, only=only)
        while parts:
            part = parts.pop(0)
            if isinstance(part, GeneratorToken):
                result = vmtoken(part, vm, only=only).chain(result)
            else:
                result = vminstr(part, vm).chain(result)
        for _ in result:
            selected = select(query.selection, vm)
            if selected is not _false:
                yield selected
    return plan


@modulemethod
def init(self, settings=None):
    '''Registers the implementation in this module as an
    IQueryTranslator for an object model we call "Python Object
    Model". Also we register this model as the default for the
    current :term:`registry`.

    .. warning::

       Don't call this method in your own code, since it will
       override all of your query-related configuration.

       This is only intended to allow testing of the translation
       common framework by configuring query translator that searches
       over Python's VM memory.

    '''
    from zope.component import getSiteManager
    from zope.interface import directlyProvides
    from ..interfaces import IQueryConfiguration
    directlyProvides(self, IQueryConfiguration, IQueryTranslator)
    manager = getSiteManager()
    configurator = manager.queryUtility(IQueryConfiguration)
    if configurator:
        pass
    else:
        manager.registerUtility(self, IQueryConfiguration)
    manager.registerUtility(self, IQueryTranslator)

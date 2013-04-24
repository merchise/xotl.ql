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
from xotl.ql.expressions import _false
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
from xotl.ql.expressions import MinFunction
from xotl.ql.expressions import MaxFunction
from xotl.ql.expressions import AllFunction
from xotl.ql.expressions import AnyFunction
from xotl.ql.expressions import SumFunction

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
            return real_operation(self._get_current_value())
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
            value = self._get_current_value()
            if isinstance(other, var):
                other = other._get_current_value()
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
            value = self._get_current_value()
            if isinstance(other, var):
                other = other._get_current_value()
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

    def __repr__(self):
        with context(UNPROXIFING_CONTEXT):
            return "<var for '%s'>" % self.term


class _object(object):
    '''The type for objects build by ``new(object, ...)``.'''
    def __init__(self, **kwargs):
        self.__dict__ = kwargs.copy()


def var_extract(maybe, default=Unset):
    if isinstance(maybe, var):
        return maybe._get_current_value(default)
    elif isinstance(maybe, vminstr.mylambda):
        return maybe()
    else:
        return maybe


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

        def extract_args(func):
            from functools import wraps
            @wraps(func)
            def inner(*args, **kwargs):
                args = tuple(var_extract(arg) for arg in args)
                kwargs = {key: var_extract(value) for key, value in kwargs.items()}
                return func(*args, **kwargs)
            return inner

        @codefor(NewObjectFunction)
        @extract_args
        def new_object(self, t, **kwargs):
            '''The implementation of the `new` function operation.'''
            if not isinstance(t, type):
                raise TypeError('The first argument to new should be a type. Not %r' % t)
            if t == object:
                return _object(**kwargs)
            else:
                return t(**kwargs)

        def sub_query_method(func):
            def inner(self, *args):
                from types import GeneratorType
                from xotl.ql.interfaces import IQueryObject
                from xotl.ql.core import these
                query, rest = args[0], args[1:]
                if rest:
                    raise SyntaxError('%s only accepts query expressions or query objects')
                if isinstance(query, GeneratorType):
                    query = these(query)
                elif not IQueryObject.providedBy(query):
                    raise SyntaxError('%s only accepts query expressions or query objects')
                plan = naive_translation(query, vm=dict(self.vm))
                return func(result for result in plan())
            return inner

        all_ = codefor(AllFunction)(extract_args(sub_query_method(all)))
        any_ = codefor(AnyFunction)(extract_args(sub_query_method(any)))
        min_ = codefor(MinFunction)(extract_args(sub_query_method(min)))
        max_ = codefor(MaxFunction)(extract_args(sub_query_method(max)))
        sum_ = codefor(SumFunction)(extract_args(sub_query_method(sum)))

        def avg(vals):
            _sum, count = 0, 0
            for x in vals:
                _sum += x
                count += 1
            return _sum/count

        average = codefor(AverageFunction)(extract_args(sub_query_method(avg)))

        # XXX: `and` and `or` don't extract all arguments unless they need it.
        @codefor(LogicalAndOperator)
        def and_(self, x, y):
            x = var_extract(x)
            if not x:
                return False
            y = var_extract(y)
            if y:
                return True
            return False

        @codefor(LogicalOrOperator)
        def or_(self, x, y):
            x = var_extract(x)
            if bool(x):
                return True
            y = var_extract(y)
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
            return not bool(x)

        table.update({
            EqualityOperator: extract_args(lambda self, x, y: x == y),
            NotEqualOperator: extract_args(lambda self, x, y: x != y),
            AdditionOperator: extract_args(lambda self, x, y: x + y),
            SubstractionOperator: extract_args(lambda self, x, y: x - y),
            DivisionOperator: extract_args(lambda self, x, y: x/y),
            MultiplicationOperator: extract_args(lambda self, x, y: x*y),
            FloorDivOperator: extract_args(lambda self, x, y: x//y),
            ModOperator: extract_args(lambda self, x, y: x % y),
            PowOperator: extract_args(lambda self, x, y: x**y),
            LeftShiftOperator: extract_args(lambda self, x, y: x << y),
            RightShiftOperator: extract_args(lambda self, x, y: x >> y),
            LesserThanOperator: extract_args(lambda self, x, y: x < y),
            LesserOrEqualThanOperator: extract_args(lambda self, x, y: x <= y),
            GreaterThanOperator: extract_args(lambda self, x, y: x > y),
            GreaterOrEqualThanOperator: extract_args(lambda self, x, y: x >= y),
            ContainsExpressionOperator: extract_args(lambda self, x, y: y in x),
            IsInstanceOperator: extract_args(lambda self, x, y: isinstance(x, y)),
            LengthFunction: extract_args(lambda self, x: len(x)),
            CountFunction: extract_args(lambda self, x: len(x)),
            PositiveUnaryOperator: extract_args(lambda self, x: +x),
            NegativeUnaryOperator: extract_args(lambda self, x: -x),
            AbsoluteValueUnaryFunction: extract_args(lambda self, x: abs(x)),
            InvokeFunction: extract_args(lambda self, m, *a, **kw: m(*a, **kw))
        })

    class mylambda(object):
        def __init__(self, code, *args, **kwargs):
            self.code = code
            self.args = args
            self.kwargs = kwargs

        def __call__(self):
            return self.code(*self.args, **self.kwargs)


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
                if node.operation not in self.vmcodeset.table:
                    raise TypeError('I don\'t know how to translate %r' % node.operation)
                def op():
                    a = tuple(x for x in _args)
                    kw = {k: x for k, x in iteritems_(_kwargs)}
                    return self.vmcodeset.table[node.operation](self, *a, **kw)
                return vminstr.mylambda(op)
            return node  # assumed to be as is
        return e(self.filter)

    def __call__(self, pre=None, post=None):
        tree = self.tree
        if isinstance(tree, var):
            return tree._get_current_value(default=False)
        else:
            return tree()

    def chain(self, source):
        for ob in source:
            res = self()
            if bool(res):
                yield


class vmtoken(object):
    '''Represents a token in the current VM.

    Like :class:`var` for terms, this is used to represent a token and fetch
    all the objects from it.

    '''
    def __init__(self, token, vm, query, only=None):
        from xoutil.compat import str_base
        self.token = token
        self.vm = vm
        if isinstance(only, str_base):
            only = (only, )
        self.only = only
        self._detect_class(query)

    def _detect_class(self, query):
        '''Detects the class for top-level (i.e has no parent) token.

        Finds if there is any filter containing an ``is_instance(token,
        SomeClass)``. If SomeClass has an attribute `this_instances` and it
        returns an iterable, it is assumed it will yield all objects from this
        class.

        '''
        token = self.token
        term = token.expression
        with context(UNPROXIFING_CONTEXT):
            parent = term.parent
        if not parent:
            from xotl.ql.expressions import is_instance, IExpressionTree
            def matches(node):
                with context(UNPROXIFING_CONTEXT):
                    return (IExpressionTree.providedBy(node) and
                            node.operation is is_instance and
                            node.children[0] == term)

            from xotl.ql.translation import cotraverse_expression
            found = next(cotraverse_expression(*query.filters, accept=matches), None)
            if found:
                self._token_class = found.children[-1]
            else:
                self._token_class = None
        else:
            self._token_class = None

    def _build_source(self):
        only = self.only
        token = self.token
        term = token.expression
        with context(UNPROXIFING_CONTEXT):
            parent = term.parent
        use_ignores = True
        if only:
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

    @property
    def source(self):
        '''The source of objects from this token.

        If then token is a top-level one and is related with a
        ``is_instance(token, SomeClass)`` filter and
        ``SomeClass.this_instances`` is a collection, this collection will be
        the source.

        If the token is a top-level token but the test described above fails,
        the we use the `gc` module to get every possible object in the Python's
        memory.

        If the token is not a top-level token, we simply use the attribute's
        name from the parent token current value.

        '''
        from xoutil.types import is_collection
        cls = self._token_class
        this_instances = getattr(cls, 'this_instances', None)
        if is_collection(this_instances):
            if not self.only or defined(cls, self.only):
                return iter(this_instances)
            else:
                return []
        else:
            return self._build_source()

    def __iter__(self):
        vm = self.vm
        token = self.token
        for ob in self.source:
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
        from xoutil.objects import get_first_of
        from xotl.ql.expressions import _false
        parts = list(sorted_parts[:])
        vm = get_first_of((plan_kwargs, kwargs), 'vm', default={})
        # vm = plan_kwargs.get('vm', None) or kwargs.get('vm', None) or {}
        result = vmtoken(parts.pop(0), vm, query, only=only)
        while parts:
            part = parts.pop(0)
            if isinstance(part, GeneratorToken):
                result = vmtoken(part, vm, query, only=only).chain(result)
            else:
                result = vminstr(part, vm).chain(result)
        for _ in result:
            selected = select(query.selection, vm)
            if selected is not _false:
                yield selected

    if query.ordering:
        def plan_with_ordering(**plan_kwargs):
            vm = plan_kwargs.setdefault('vm', {})
            key = lambda: tuple(vminstr(order_expr, vm=vm)() for order_expr in query.ordering)
            # XXX: Don't use sorted(plan(**plan_kwargs), key=key)
            #
            #      Since the vm is constantly being updated after each yield we
            #      must make sure, key() is called exactly when the vm has the
            #      desired state for each object; but sorted may retreive
            #      several items in chunks and call key aftewards which will
            #      not yield the right results.
            return (sel for k, sel in sorted((key(), r) for r in plan(**plan_kwargs)))
        res = plan_with_ordering
    else:
        res = plan
    if query.partition:
        from xoutil.objects import extract_attrs
        start, stop, step = extract_attrs(query.partition, 'start', 'stop',
                                          'step')
        def plan_with_partition(**kwargs):
            from itertools import islice
            return islice(res(**kwargs), start, stop, step)
        return plan_with_partition
    return res


@modulemethod
def init(self, settings=None):
    '''Registers the implementation in this module as an IQueryTranslator for
    an object model we call "Python Object Model".

    .. warning::

       Don't call this method in your own code, since it will override all of
       your query-related configuration.

       This is only intended to allow testing of the translation common
       framework by configuring query translator that searches over Python's VM
       memory.

    '''
    from zope.component import getSiteManager
    from zope.interface import directlyProvides
    from ..interfaces import IQueryConfigurator, IQueryTranslator
    directlyProvides(self, IQueryConfigurator)
    directlyProvides(self.naive_translation, IQueryTranslator)
    manager = getSiteManager()
    manager.registerUtility(self, IQueryConfigurator)


@modulemethod
def get_translator(self):
    return self.naive_translation

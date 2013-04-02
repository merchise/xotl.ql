#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#----------------------------------------------------------------------
# xotl.ql.translate
#----------------------------------------------------------------------
# Copyright (c) 2012, 2013 Merchise Autrement and Contributors
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under
# the terms of the LICENCE attached in the distribution package.
#
# Created on Jul 2, 2012

'''The main purposes of this module are two:

- To provide common query/expression translation framework from query
  objects to data store languages.

- To provide a testing bed for queries to retrieve real objects from
  somewhere (in this case the Python's).

'''

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

from zope.interface import Interface

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

from xotl.ql.interfaces import (ITerm,
                                IGeneratorToken,
                                IExpressionTree,
                                IQueryTranslator)

__docstring_format__ = 'rst'
__author__ = 'manu'


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


def _instance_of(which):
    '''Returns an `accept` filter for :func:`_iter_objects` or
    :func:`_iter_classes` that only accepts objects that are instances of
    `which`; `which` may be either a class or an Interface
    (:mod:`!zope.interface`).

    '''
    def accept(ob):
        return isinstance(ob, which) or (issubclass(which, Interface) and
                                         which.providedBy(ob))
    return accept


def cotraverse_expression(*expressions, **kwargs):
    '''Coroutine that traverses expression trees an yields every node that
    matched the `accept` predicate. If `accept` is None it defaults to accept
    only :class:`~xotl.ql.interface.ITerm` instances that have a non-None
    `name`.

    :param expressions: Several :term:`expression tree` objects (or
                        :term:`query objects <query object>`) to traverse.

    :param accept: A function that is passed every node found the trees that
                   must return True if the node should be yielded.

    Coroutine behavior:

    You may reintroduce both `expr` and `accept` arguments by sending messages
    to this coroutine. The message may be:

    - A single callable value, which will replace `accept`.

    - A single non callable value, which will be considered *another*
      expression to process. Notice this won't make `cotraverse_expression` to
      stop considering all the nodes from previous expressions. However, the
      expression might be explored before other later generated children of the
      previous expressions.

    - A tuple consisting in `(expr, accept)` that will be treated like the
      previous cases.

    - A dict that may have `expr` and `accept` keys.

    The default behavior helps to catch all named
    :class:`xotl.ql.interfaces.ITerm` instances in an expression. This is
    useful for finding every "name" in a query, which may not appear in the
    query selection. For instance we, may have a model that relates Person
    objects indirectly via a Relation object::

        >>> from xotl.ql.core import thesefy
        >>> @thesefy()
        ... class Person(object):
        ...     pass

        >>> @thesefy()
        ... class Relation(object):
        ...    pass

    Then, for the following query::

        >>> from xotl.ql.core import these
        >>> from xoutil.compat import izip
        >>> query = these((person, partner)
        ...               for person, partner in izip(Person, Person)
        ...               for rel in Relation
        ...               if (rel.subject == person) & (rel.obj == partner))

    if we need to find every single named term in the filters of the query, we
    would see that there are seven:

    - `person`, `partner` and `rel` (as given by the `is_instance(...)`
      filters ``@thesefy`` injects)

    - `rel.subject`, `person`, `rel.obj` and `partner` in the explicit
       filter::

        >>> len(list(cotraverse_expression(*query.filters)))
        7

    '''
    is_expression = IExpressionTree.providedBy
    accept = kwargs.get('accept', lambda x: _instance_of(ITerm)(x) and x.name)
    with context(UNPROXIFING_CONTEXT):
        queue = list(expressions)
        while queue:
            current = queue.pop(0)
            msg = None
            if accept(current):
                msg = yield current
            if is_expression(current):
                queue.extend(current.children)
                named_children = current.named_children
                queue.extend(named_children[key] for key in named_children)
            if msg:
                if callable(msg):
                    accept = msg
                elif isinstance(msg, tuple):
                    expr, accept = msg
                    queue.append(expr)
                elif isinstance(msg, dict):
                    expr = msg.get('expr', None)
                    if expr:
                        queue.append(expr)
                    accept = msg.get('accept', accept)
                else:
                    queue.append(msg)


def cocreate_plan(query, **kwargs):
    '''**Not implemented yet**. The documentation provided is just an idea.

    Builds a :term:`query execution plan` for a given query that fetches
    objects from Python's VM memory.

    This function is meant to be general enough so that other may use
    it as a base for building their :term:`translators <query
    translator>`.

    It works like this:

    1. First it inspect the tokens and their relations (if a token is
       the parent of another). For instance in the query::

           query = these((parent, child)
                         for parent in this
                         if parent.children & (parent.age > 34)
                         for child in parent.children if child.age < 5)

       The `parent.children` generator tokens is *derived* from the
       token `this`, so there should be a relation between the two.

       .. todo::

          If we allow to have subqueries, it's not clear how to
          correlate tokens. A given token may be a whole query::

              p = these((parent, partner)
                        for parent in this('parent')
                        for partner, _ in subquery((partner, partner.depth())
                                            for partner in this
                                            if contains(partner.related_to,
                                                        parent)))

          Since all examples so far of sub-queries as generators
          tokens are not quite convincing, we won't consider that.

    '''
    pass


def _to_python_expression(expression):
    with context(UNPROXIFING_CONTEXT):
        if ITerm.providedBy(expression):
            parent = expression.parent
            if parent is None:
                return expression.name
            else:
                return _to_python_expression(expression.parent) + '.' + expression.name
        elif IExpressionTree.providedBy(expression):
            operation = expression.operation
            result = operation.arity.formatter(operation,
                                               expression.children,
                                               expression.named_children,
                                               _str=_to_python_expression)
            return result
        else:
            return repr(expression)


def evaluate(expression, table):
    expr = _to_python_expression(expression)
    return eval(expr, table, table)


def cmp_terms(t1, t2, strict=False):
    '''Compares two terms in a partial order.

    This is a *partial* compare operator. A term `t1 < t2` if and only if `t1` is
    in the parent-chain of `t2`.

    If `strict` is False the comparison between expressions will be made with
    the `eq` operation; otherwise `is` will be used.

    If either `t1` or `t2` are generator tokens it's
    :attr:`~xotl.ql.interfaces.IGeneratorToken.expression` is used instead.

    Examples::

        >>> from xotl.ql.core import this, these
        >>> t1 = this('a').b.c
        >>> t2 = this('b').b.c.d
        >>> t3 = this('a').b

        >>> cmp_terms(t1, t3)
        1

        # But if equivalence is False neither t1 < t3 nor t3 < t1 holds.
        >>> cmp_terms(t1, t3, True)
        0

        # Since t1 and t2 have no comon ancestor, they are not ordered.
        >>> cmp_terms(t1, t2)
        0

        >>> query = these((child, brother)
        ...               for parent in this
        ...               for child in parent.children
        ...               for brother in parent.children
        ...               if child is not brother)

        >>> t1, t2, t3 = query.tokens

        >>> cmp_terms(t1, t2)
        -1

        >>> cmp_terms(t2, t3)
        0

    '''
    import operator
    if not strict:
        test = operator.eq
    else:
        test = operator.is_
    with context(UNPROXIFING_CONTEXT):
        if IGeneratorToken.providedBy(t1):
            t1 = t1.expression
        if IGeneratorToken.providedBy(t2):
            t2 = t2.expression
        if test(t1, t2):
            return 0
        else:
            t = t1
            while t and not test(t, t2):
                t = t.parent
            if t:
                return 1
            t = t2
            while t and not test(t, t1):
                t = t.parent
            if t:
                return -1
            else:
                return 0


def token_before_filter(tk, expr, strict=False):
    '''Partial order (`<`) compare function between a token (or term) and an
    expression.

    A token *is before* an expression if it is (or is before of) the binding of
    the terms in the expression.

    '''
    with context(UNPROXIFING_CONTEXT):
        def check(term):
            if tk is term.binding:
                return True
            else:
                return cmp_terms(tk, term.binding, strict) == -1
        return any(check(term) for term in cotraverse_expression(expr))

def cmp(a, b, strict=False):
    '''Partial compare function between tokens and expressions.

    Examples::

       >>> from xotl.ql import this, these
       >>> query = these((parent, child)
       ...               for parent in this
       ...               for child in parent.children
       ...               if parent.age > 34
       ...               if child.age < 6)

       >>> parent_token, children_token = query.tokens
       >>> expr1, expr2 = query.filters

       >>> cmp(parent_token, expr1)
       -1

       >>> cmp(children_token, parent_token)
       1

       >>> cmp(expr1, children_token)
       0

       >>> import functools
       >>> l = [expr1, expr2, parent_token, children_token]
       >>> l.sort(key=functools.cmp_to_key(cmp))
       >>> expected = [parent_token, expr1, children_token, expr2]
       >>> all(l[i] is expected[i] for i in (0, 1, 2, 3))
       True
    '''
    from ..interfaces import IExpressionCapable
    with context(UNPROXIFING_CONTEXT):
        if IGeneratorToken.providedBy(a) and IGeneratorToken.providedBy(b):
            return cmp_terms(a, b, strict)
        elif IGeneratorToken.providedBy(a) and IExpressionCapable.providedBy(b):
            return -1 if token_before_filter(a, b, strict) else 0
        elif IExpressionCapable.providedBy(a) and IGeneratorToken.providedBy(b):
            return 1 if token_before_filter(b, a, strict) else 0
        else:
            return 0


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
            if default is not Unset:
                return default
            elif not path:
                # XXX: We return _false if the path was completely consumed,
                # i.e: the failure point is the last attribute. I (manu) think
                # is less astonishing to return a falsy value than to fail. Of
                # course this works only for truth-testing; for traversing, a
                # _false token should yield nothing.
                return _false
            else:
                raise AttributeError(step or root)
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


class vmfilter(object):
    '''Represents a filter ready to be executed in the VM current state.'''

    table = {EqualityOperator: lambda x, y: x == y,
             NotEqualOperator: lambda x, y: x != y,
             LogicalAndOperator: lambda x, y: x & y,
             LogicalOrOperator: lambda x, y: x | y,
             LogicalXorOperator: lambda x, y: x ^ x,
             LogicalNotOperator: lambda x: ~x,
             AdditionOperator: lambda x, y: x + y,
             SubstractionOperator: lambda x, y: x - y,
             DivisionOperator: lambda x, y: x/y,
             MultiplicationOperator: lambda x, y: x*y,
             FloorDivOperator: lambda x, y: x//y,
             ModOperator: lambda x, y: x % y,
             PowOperator: lambda x, y: x**y,
             LeftShiftOperator: lambda x, y: x << y,
             RightShiftOperator: lambda x, y: x >> y,
             LesserThanOperator: lambda x, y: x < y,
             LesserOrEqualThanOperator: lambda x, y: x <= y,
             GreaterThanOperator: lambda x, y: x > y,
             GreaterOrEqualThanOperator: lambda x, y: x >= y,
             ContainsExpressionOperator: lambda x, y: y in x,
             IsInstanceOperator: lambda x, y: x._is_a(y),
             LengthFunction: lambda x: len(x),
             CountFunction: lambda x: len(x),
             PositiveUnaryOperator: lambda x: +x,
             NegativeUnaryOperator: lambda x: -x,
             AbsoluteValueUnaryFunction: lambda x: abs(x),
             InvokeFunction: lambda m, *a, **kw: m(*a, **kw)}

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
                assert node.operation in self.table, 'I don\'t know how to translate %r' % node.operation
                return lambda: self.table[node.operation](*_args, **_kwargs)
            return node # assumed to be as is
        return e(self.filter)


    def _exec(self, instruction):
        inst, args = instruction[0], instruction[1:]
        if inst == 'set':
            which, what = args
            self.vm[which] = what
            return ('del', which)
        elif inst == 'del':
            which = args[0]
            del self.vm[which]

    # @contextlib.contextmanager
    # def modify_vm(self, pre=None, post=None):
    #     if pre:
    #         _post = self._exec(pre)
    #         if not post and _post:
    #             post = _post
    #     yield self
    #     if post:
    #         self._exec(post)

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
                # import ipdb; ipdb.set_trace()
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
    only = kwargs.get('only', None)
    def mix(filters, tokens):
        '''Intertwines tokens and filters.'''
        # TODO: Improve algorithm.
        if not filters:
            return tokens
        result = list(filters + tokens)
        for i in range(len(result)-1):
            for j in range(i+1, len(result)):
                if cmp(result[i], result[j]) > 0:
                    result[i], result[j] = result[j], result[i]
        return result

    def select(sel, vm):
        from xotl.ql.expressions import _false
        result = []
        selectors = (sel, ) if not isinstance(sel, tuple) else sel
        for s in selectors:
            if isinstance(s, Term):
                result.append(var(s, vm)._get_current_value())
            else:
                result.append(vmfilter(s, vm)())
        if any(res is _false for res in result):
            return _false
        if isinstance(sel, tuple):
            return tuple(result)
        else:
            assert len(result) == 1
            return result[0]

    def plan():
        # The algorithm is simple; first we "intertwine" tokens and filters
        # using a (stable) partial order: a filter comes before a token if and
        # only if neither of it's terms is bound to the token.
        #
        # The we just build several chained generators that either produce
        # (affect the vm) or filter.
        #
        from xotl.ql.expressions import _false
        parts = mix(query.filters, query.tokens)
        vm = {}
        assert isinstance(parts[0], GeneratorToken), parts
        result = vmtoken(parts.pop(0), vm, only=only)
        while parts:
            part = parts.pop(0)
            if isinstance(part, GeneratorToken):
                result = vmtoken(part, vm, only=only).chain(result)
            else:
                result = vmfilter(part, vm).chain(result)
        return (select(query.selection, vm)
                for _ in result
                if select(query.selection, vm) is not _false)
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

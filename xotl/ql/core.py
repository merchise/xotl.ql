#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------
# Copyright (c) Merchise Autrement [~º/~] and Contributors
# All rights reserved.
#
# This is free software; you can do what the LICENCE file allows you to.
#

'''The query language core.

'''

import ast
import types
from xoutil.symbols import Unset
from xoutil.objects import memoized_property
from collections import MappingView, Mapping

from xoutil.decorator.meta import decorator

from xotl.ql import interfaces


class Universe:
    '''The class of the `this`:obj: object.

    The `this` object is simply a name from which objects can be drawn in a
    query.

    '''
    def __new__(cls):
        res = getattr(cls, 'instance', None)
        if not res:
            res = super().__new__(cls)
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
    'limit', 'offset', 'groups', 'order', 'get_value', 'qst', '_frame'
)


class QueryObject:
    frame_type = 'xotl.ql.core.Frame'

    def __init__(self, qst, _frame, **kwargs):
        self.qst = qst
        self._frame = _frame
        if any(name in RESERVED_ARGUMENTS for name in kwargs):
            raise TypeError('Invalid keyword argument')
        self.expression = kwargs.pop('expression', None)
        for attr, val in kwargs.items():
            setattr(self, attr, val)

    def get_value(self, name, only_globals=False):
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

    @memoized_property
    def locals(self):
        return self._frame.f_locals

    @memoized_property
    def globals(self):
        return self._frame.f_globals

    @memoized_property
    def source(self):
        builder = SourceBuilder()
        return builder.get_source(self.qst)


def get_query_object(generator,
                     query_type='xotl.ql.core.QueryObject',
                     frame_type=None,
                     **kwargs):
    '''Get the query object from a query expression.

    '''
    from xoutil.objects import import_object
    from xotl.ql.revenge import Uncompyled
    uncompiled = Uncompyled(generator)
    gi_frame = generator.gi_frame
    QueryObjectType = import_object(query_type)
    FrameType = import_object(frame_type or QueryObjectType.frame_type)
    return QueryObjectType(
        uncompiled.qst,
        FrameType(gi_frame.f_locals, gi_frame.f_globals),
        expression=generator,
        **kwargs
    )


# Alias to the old API.
these = get_query_object


def get_predicate_object(func, predicate_type='xotl.ql.core.QueryObject',
                         frame_type=None, **kwargs):
    '''Get a predicate object from a predicate expression.

    '''
    from xoutil.objects import import_object
    from .revenge import Uncompyled
    uncompiled = Uncompyled(func)
    PredicateClass = import_object(predicate_type)
    FrameClass = import_object(frame_type or PredicateClass.frame_type)
    return PredicateClass(
        uncompiled.qst,
        FrameClass(_get_closure(func), func.__globals__),
        predicate=func,
        **kwargs
    )


def normalize_query(which, **kwargs):
    '''Ensure a query object.

    If `which` is a query expression (more precisely a generator object) it is
    passed to `get_query_object`:func: along with all keyword arguments.

    If `which` is not a query expression it must be a `query object`:term:,
    other types are a TypeError.

    '''
    from types import GeneratorType
    if isinstance(which, GeneratorType):
        return get_query_object(which, **kwargs)
    else:
        if not isinstance(which, interfaces.QueryObject):
            raise TypeError('Query object expected, but object provided '
                            'is not: %r' % type(which))
        return which


@decorator
def thesefy(target, make_subquery=True):
    '''Allow an object to participate in queries.

    Example as a wrapper::

        class People:
            # ...
            pass

        query = (who for who in thesefy(People))

    Example as a decorator::

        @thesefy
        class People:
            pass

        query = (who for who in People)

    If `target` already support the iterable protocol (i.e implement
    ``__iter__``), return it unchanged.

    If `make_subquery` is True, then the query shown above will be equivalent
    to::

        query = (who for who in (x for x in this if isinstance(x, People)))

    If `make_subquery` is False, `thesefy` injects an ``__iter__()`` that
    simply returns the same object and a ``next()`` method that immediately
    stops the iteration.

    Notice that in order to use `make_subquery` you call `thesefy`:func: as a
    decorator-returning function::

        class Person:
            pass

        query = (x for x in thesefy(make_subquery=False)(Person))

        # or simply as a decorator

        @thesefy(make_subquery=False)
        class Person:
            pass

    '''
    if getattr(target, '__iter__', None):
        return target

    class new_meta(type(target)):
        if make_subquery:
            def __iter__(self):
                return (x for x in this if isinstance(x, self))
        else:
            def __iter__(self):
                return self

            def next(self):
                raise StopIteration
            __next__ = next

    from xoutil.objects import copy_class
    new_class = copy_class(target, meta=new_meta)
    return new_class


class Frame:
    def __init__(self, locals, globals, **kwargs):
        self.auto_expand_subqueries = kwargs.pop('auto_expand_subqueries',
                                                 True)
        self.f_locals = _FrameView(locals)
        self.f_globals = _FrameView(globals)
        self.f_locals.owner = self.f_globals.owner = self


class _FrameView(MappingView, Mapping):
    def __contains__(self, key):
        try:
            self[key]
        except KeyError:
            return False
        else:
            return True

    def __getitem__(self, key):
        res = self._mapping[key]
        if self.owner.auto_expand_subqueries and key == '.0':
            return sub_query_or_value(res)
        else:
            return res

    def get(self, key, default=None):
        res = self._mapping.get(key, default)
        if self.owner.auto_expand_subqueries and key == '.0':
            return sub_query_or_value(res)
        else:
            return res

    def __iter__(self):
        return iter(self._mapping)


def _get_closure(obj):
    assert isinstance(obj, types.FunctionType)
    if obj.__closure__:
        return {
            name: cell.cell_contents
            for name, cell in zip(obj.__code__.co_freevars, obj.__closure__)
        }
    else:
        return {}


def sub_query_or_value(v):
    if isinstance(v, types.GeneratorType) and v.gi_code.co_name == '<genexpr>':
        return get_query_object(v)
    else:
        return v


class SourceBuilder(ast.NodeVisitor):
    def get_source(self, node):
        stack = self.stack = []
        self.visit(node)
        assert len(stack) == 1, 'Remaining items %r at %r' % (stack, node)
        return stack.pop()

    def visit_And(self, node):
        self.stack.append(' and ')

    def visit_Or(self, node):
        self.stack.append(' or ')

    def visit_Name(self, node):
        self.stack.append(node.id)

    def visit_BoolOp(self, node):
        self.visit(node.op)
        for val in node.values:
            self.visit(val)
        exprs = []
        for _ in range(len(node.values)):
            exprs.insert(0, self.stack.pop(-1))
        op = self.stack.pop(-1)
        self.stack.append('(%s)' % op.join(exprs))

    def visit_BinOp(self, node):
        stack = self.stack
        self.visit(node.op)
        self.visit(node.right)
        self.visit(node.left)
        left = stack.pop(-1)
        right = stack.pop(-1)
        op = stack.pop(-1)
        stack.append('(%s%s%s)' % (left, op, right))

    def visit_Add(self, node):
        self.stack.append(' + ')

    def visit_Sub(self, node):
        self.stack.append(' - ')

    def visit_Mult(self, node):
        self.stack.append(' * ')

    def visit_Div(self, node):
        self.stack.append(' / ')

    def visit_Mod(self, node):
        self.stack.append(' % ')

    def visit_Pow(self, node):
        self.stack.append(' ** ')

    def visit_LShift(self, node):
        self.stack.append(' << ')

    def visit_RShift(self, node):
        self.stack.append(' >> ')

    def visit_BitOr(self, node):
        self.stack.append(' | ')

    def visit_BitAnd(self, node):
        self.stack.append(' & ')

    def visit_BitXor(self, node):
        self.stack.append(' ^ ')

    def visit_FloorDiv(self, node):
        self.stack.append(' // ')

    def visit_Num(self, node):
        self.stack.append('%s' % node.n)

    def visit_UnaryOp(self, node):
        stack = self.stack
        self.visit(node.op)
        self.visit(node.operand)
        operand = stack.pop(-1)
        op = stack.pop(-1)
        stack.append('(%s%s)' % (op, operand))

    def visit_Invert(self, node):
        self.stack.append('~')

    def visit_Not(self, node):
        self.stack.append('not ')

    def visit_UAdd(self, node):
        self.stack.append('+')

    def visit_USub(self, node):
        self.stack.append('-')

    def visit_IfExp(self, node):
        self.visit(node.orelse)
        self.visit(node.test)
        self.visit(node.body)
        body = self.stack.pop(-1)
        test = self.stack.pop(-1)
        orelse = self.stack.pop(-1)
        self.stack.append('(%s if %s else %s)' % (body, test, orelse))

    def visit_Lambda(self, node):
        raise NotImplementedError()

    def visit_Dict(self, node):
        # order does not really matter but I'm picky
        for k, v in reversed(zip(node.keys, node.values)):
            self.visit(v)
            self.visit(k)
        dictbody = ', '.join(
            '%s: %s' % (self.stack.pop(-1), self.stack.pop(-1))
            for _ in range(len(node.keys))
        )
        self.stack.append('{%s}' % dictbody)

    def visit_Set(self, node):
        for elt in reversed(node.elts):
            self.visit(elt)
        setbody = ', '.join(self.stack.pop(-1) for _ in range(len(node.elts)))
        self.stack.append('{%s}' % setbody)

    def visit_ListComp(self, node):
        self._visit_comp(node)
        self.stack.append('[%s]' % self.stack.pop(-1))

    def visit_SetComp(self, node):
        self._visit_comp(node)
        self.stack.append('{%s}' % self.stack.pop(-1))

    def visit_DictComp(self, node):
        self.visit(node.value)
        self.visit(node.key)
        pop = lambda: self.stack.pop(-1)
        lines = ['%s: %s' % (pop(), pop())]
        self._visit_generators(node)
        lines.append(pop())
        self.stack.append('{%s}' % ' '.join(lines))

    def visit_GeneratorExp(self, node):
        self._visit_comp(node)
        self.stack.append('(%s)' % self.stack.pop(-1))

    def _visit_comp(self, node):
        self.visit(node.elt)
        pop = lambda: self.stack.pop(-1)
        lines = [pop()]
        self._visit_generators(node)
        lines.append(pop())
        self.stack.append(' '.join(lines))

    def _visit_generators(self, node):
        for comp in reversed(node.generators):
            for if_ in reversed(comp.ifs):
                self.visit(if_)
            self.stack.append(len(comp.ifs))  # save the length of ifs [*]
            self.visit(comp.iter)
            self.visit(comp.target)
        pop = lambda: self.stack.pop(-1)
        lines = []
        for _ in range(len(node.generators)):
            lines.append('for %s in %s' % (pop(), pop()))
            for if_ in range(pop()):  # [*] pop the length of ifs
                lines.append('if %s' % pop())
        self.stack.append(' '.join(lines))

    def visit_Yield(self, node):
        raise TypeError('Invalid node Yield')

    def visit_Eq(self, node):
        self.stack.append(' == ')

    def visit_NotEq(self, node):
        self.stack.append(' != ')

    def visit_Lt(self, node):
        self.stack.append(' < ')

    def visit_LtE(self, node):
        self.stack.append(' <= ')

    def visit_Gt(self, node):
        self.stack.append(' > ')

    def visit_GtE(self, node):
        self.stack.append(' >= ')

    def visit_Is(self, node):
        self.stack.append(' is ')

    def visit_IsNot(self, node):
        self.stack.append(' is not ')

    def visit_In(self, node):
        self.stack.append(' in ')

    def visit_NotIn(self, node):
        self.stack.append(' not in ')

    def visit_Compare(self, node):
        self.visit(node.left)
        for op, expr in reversed(zip(node.ops, node.comparators)):
            self.visit(expr)
            self.visit(op)
        right = ''.join(
            # I assume each operator has spaces around it
            '%s%s' % (self.stack.pop(-1), self.stack.pop(-1))
            for _ in range(len(node.ops))
        )
        self.stack.append('%s%s' % (self.stack.pop(-1), right))

    def visit_Call(self, node):
        if node.kwargs:
            self.visit(node.kwargs)
        if node.starargs:
            self.visit(node.starargs)
        for kw in reversed(node.keywords):
            self.visit(kw.value)
            self.stack.append(kw.arg)
        for arg in reversed(node.args):
            self.visit(arg)
        self.visit(node.func)
        func = self.stack.pop(-1)
        args = [self.stack.pop(-1) for _ in range(len(node.args))]
        keywords = [
            (self.stack.pop(-1), self.stack.pop(-1))
            for _ in range(len(node.keywords))
        ]
        starargs = self.stack.pop(-1) if node.starargs else ''
        kwargs = self.stack.pop(-1) if node.kwargs else ''
        call = ', '.join(args)
        if keywords:
            if call:
                call += ', '
            call += ', '.join('%s=%s' % (k, v) for k, v in keywords)
        if starargs:
            if call:
                call += ', '
            call += '*%s' % starargs
        if kwargs:
            if call:
                call += ', '
            call += '**%s' % kwargs
        self.stack.append('%s(%s)' % (func, call))

    def visit_Str(self, node):
        self.stack.append('%r' % node.s)

    visit_Bytes = visit_Str

    def visit_Repr(self, node):
        raise NotImplementedError

    def visit_Attribute(self, node):
        self.visit(node.value)
        self.stack.append('%s.%s' % (self.stack.pop(-1), node.attr))

    def visit_Subscript(self, node):
        self.visit(node.slice)
        self.visit(node.value)
        self.stack.append('%s[%s]' % (self.stack.pop(-1), self.stack.pop(-1)))

    def visit_Ellipsis(self, node):
        self.stack.append('...')

    def visit_Slice(self, node):
        if node.step:
            self.visit(node.step)
            step = self.stack.pop(-1)
        else:
            step = None
        if node.upper:
            self.visit(node.upper)
            upper = self.stack.pop(-1)
        else:
            upper = None
        if node.lower:
            self.visit(node.lower)
            lower = self.stack.pop(-1)
        else:
            lower = None
        if lower:
            res = '%s:' % lower
        else:
            res = ':'
        if upper:
            res += '%s' % upper
        if step:
            res += ':%s' % step
        self.stack.append(res)

    def visit_List(self, node):
        for elt in reversed(node.elts):
            self.visit(elt)
        self.stack.append(
            '[%s]' % ', '.join(
                self.stack.pop(-1) for _ in range(len(node.elts))
            )
        )

    def visit_Tuple(self, node):
        for elt in reversed(node.elts):
            self.visit(elt)
        result = (
            '(%s' % ', '.join(
                self.stack.pop(-1) for _ in range(len(node.elts))
            )
        )
        if len(node.elts) == 1:
            result += ', )'
        else:
            result += ')'
        self.stack.append(result)


del decorator

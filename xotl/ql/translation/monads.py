#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------
# Copyright (c) Merchise Autrement [~º/~] and Contributors
# All rights reserved.
#
# This is free software; you can do what the LICENCE file allows you to.
#

'''Monad comprehensions.

.. warning:: As noted in [QLFunc]_ algebra operators are an "abstraction of
   the algorithms implemented by target query engines."  Therefore, the
   following implementation of such operators are not designed to provide an
   efficient representation of those algorithms and data structures.

'''

import operator

from xoutil.symbols import Undefined
from xoutil.infinity import Infinity

from xotl.ql import qst

import sys
_py_version = sys.version_info
_py3 = _py_version >= (3, 0)
del sys


class Type:
    'An algebra as a type.'
    pass


class Empty(Type):
    '''Any empty collection.

    '''
    def __new__(cls):
        '''Create the singleton instance of Empty.

        The following are always True:

          >>> Empty() is Empty()
          True

          >>> isinstance(Empty(), Empty)
          True

        '''
        instance = getattr(cls, 'instance', None)
        if instance is None:
            res = super().__new__(cls)
            res.__init__()
            cls.instance = res
            return res
        else:
            return instance

    def __repr__(self):
        return 'Empty()'

    def __unicode__(self):
        return '∅'.decode('utf-8')

    def __iter__(self):
        return iter([])

    def __bool__(self):
        return False
    __nonzero__ = __bool__

    def iter(self):
        return iter([])

    def list(self):
        return list(self.iter())

    def set(self):
        return set(self.iter())


class _BaseCons:
    @staticmethod
    def _head(collection):
        def _inner():
            i = iter(collection)
            yield next(i)
            try:
                peek = next(i)
            except StopIteration:
                yield Empty()
            else:
                from itertools import chain
                yield chain((peek, ), (x for x in i))
        if not isinstance(collection, Empty):
            return _inner()
        else:
            raise ValueError('Cannot extract the head of an empty collection.')

    def __bool__(self):
        return bool(self.x)
    __nonzero__ = __bool__

    def __call__(self, *args):
        if not args:
            return self
        x, xs = self.x, self.xs
        if x is not Undefined and xs is not Undefined:
            raise TypeError('Fully qualified Cons')
        if x is Undefined and args:
            x, args = args[0], args[1:]
        if xs is Undefined and args:
            xs, args = args[0], args[1:]
        assert not args
        return type(self)(x, xs)

    def iter(self):
        assert self.xs is not Undefined and self.x is not Undefined
        head, tail = self
        yield head
        while not isinstance(tail, Empty):
            head, tail = tail
            yield head

    def list(self):
        return list(self.iter())

    def set(self):
        return set(self.iter())

    def __repr__(self):
        if self.xs is not Undefined:
            return '%s(%r, %r)' % (type(self).__name__, self.x, self.xs)
        else:
            return '%s(%r)' % (type(self).__name__, self.x)


class Cons(_BaseCons, Type):
    r'''The collection constructor "x : xs".

    The basic usage is:

       >>> Cons(1, [])
       Cons(1, Empty())

    That builds the collection with a single element, the `Empty()` being the
    empty collection.

    '''
    def __init__(self, *args):
        from collections import Iterable
        x, xs = Undefined, Undefined
        if args:
            x, args = args[0], args[1:]
        if args:
            xs, args = args[0], args[1:]
        assert not args
        self.x = x
        if isinstance(xs, Cons):
            self.xs = xs
        elif isinstance(xs, Iterable) and not isinstance(xs, Empty):
            xxs = tuple(Cons._head(xs))
            if xxs:
                self.xs = Cons(*xxs)
            else:
                self.xs = Empty()
        elif isinstance(xs, Iterable) and isinstance(xs, Empty):
            self.xs = Empty()
        else:
            self.xs = xs

    def __iter__(self):
        def _iter():
            yield self.x
            yield self.xs

        if self.x is not Undefined and self.xs is not Undefined:
            return _iter()
        else:
            raise TypeError('Cons as a partial function cannot be iterated')


class LazyCons(_BaseCons, Type):
    '''A Cons that does not iterate over its arguments until needed.

    `Cons`:class: can't represent a collection that exceeds the recursion
    limit of the underlying representation.  LazyCons can represent such
    collections:

      >>> from xotl.ql.translation.monads import LazyCons
      >>> from xoutil.eight import range
      >>> lc = LazyCons(1, range(10**6))
      >>> lc                                            # doctest: +ELLIPSIS
      LazyCons(1, ...range(...1000000))

      >>> len(lc.list())
      1000001

    As with `Cons`:class: the standard operation is to extract head and tail.
    The tail is always a `LazyCons`:class: instance:

       >>> head, tail = lc
       >>> head
       1

       >>> tail                                         # doctest: +ELLIPSIS
       LazyCons(0, <range...iterator...>)

    It may even represent unbounded collections:

       >>> import itertools
       >>> lc = LazyCons(1, itertools.count(2))
       >>> lc
       LazyCons(1, count(2))

    However you must be careful while iterating over such as collection:

       >>> len(list(itertools.takewhile(lambda x: x < 100, lc.iter())))
       99

    .. warning:: LazyCons is not provided for performance or efficiency.

       Like all the objects in this module, LazyCons is not meant to be used
       in production but to test expectations about the execution plans you
       may be using based on monads comprehensions.

       We needed a lazy version of Cons in out the
       `xotl.ql.translation.py`:mod: module

    '''
    def __init__(self, *args):
        x, xs = Undefined, Undefined
        if args:
            x, args = args[0], args[1:]
        if args:
            xs, args = args[0], args[1:]
        assert not args
        self.x = x
        self.xs = xs

    def __iter__(self):
        def _iter():
            yield self.x
            i = iter(self.xs)
            try:
                head = next(i)
                yield LazyCons(head, i)
            except StopIteration:
                yield Empty()

        if self.x is not Undefined and self.xs is not Undefined:
            return _iter()
        else:
            raise TypeError(
                'LazyCons as a partial function cannot be iterated'
            )


# Quote:
#
#   Thus, in order for `foldr + z` to be well-defined, `+` has to be
#   commutative or idempotent whenever (:) is left-commutative or
#   left-idempotent respectively.  This ensures the meaning of `foldr + z` to
#   be independent of the actual construction of its argument.
#
#   -- [QLFunc]_
class Foldr(Type):
    '''The structural recursion operator.'''
    # foldr                ::  (a -> B -> B) -> B -> T a -> B
    # foldr + z []         =   z
    # foldr + z (x : xs)   =   x + (foldr + z xs)

    def __init__(self, *args):
        operator, arg, collection, args = self._parse_args(args)
        assert not args
        self.operator = operator
        self.arg = arg
        self.collection = collection

    def __call__(self, *args):
        operator, arg, collection = self._get_args(args)
        if any(a is Undefined for a in (operator, arg, collection)):
            return Foldr(operator, arg, collection)
        if isinstance(collection, Empty):
            return arg
        else:
            x, xs = collection
            # If `operator` actually "tracks" the application of a function on
            # the too arguments we get the spine instead of the value.  See
            # Operation.
            return operator(x, Foldr(operator, arg, xs)())

    def _get_args(self, args):
        operator = self.operator
        arg = self.arg
        collection = self.collection
        if operator is Undefined and args:
            operator, args = args[0], args[1:]
        if arg is Undefined and args:
            arg, args = args[0], args[1:]
        if collection is Undefined and args:
            collection, args = args[0], args[1:]
        assert not args
        return operator, arg, collection

    @classmethod
    def _parse_args(cls, args):
        if args:
            operator, args = args[0], args[1:]
        else:
            operator = Undefined
        if args:
            z, args = args[0], args[1:]
        else:
            z = Undefined
        if args:
            ls, args = args[0], args[1:]
        else:
            ls = Undefined
        return (operator, z, ls, args)


class Operator(Type):
    '''Any operator.

    Allows to represent the application of an operator deferring the
    application.

    Useful to represent applications of an operator over a spine:

       >>> from xotl.ql.translation.monads import Map, Operator
       >>> Mapper = Map(Operator(lambda x: x + 1))

    '''
    def __init__(self, operator, *partials):
        self.operator = operator
        self.partials = partials

    def __repr__(self):
        return '<Operator(...)>'

    def __call__(self, *args):
        args = self.partials + args
        return Operator(self.operator, *args)

    def getvalue(self):
        return self.operator(*tuple(
            arg.getvalue() if isinstance(arg, Operator) else arg
            for arg in self.partials
        ))


class Union(Type):
    '''The Union operation.

    Unions are defined over `Cons`:class: instances.  Unions instances are
    callables that perform the union when called.

    Creating a Union:

      >>> from xotl.ql.translation.monads import Union, Cons
      >>> whole = Union(Cons(1, []), Cons(2, []))
      >>> whole
      Union(Cons(1, Empty()), Cons(2, Empty()))

    Calling the union instance performs the union:

      >>> whole()
      Cons(1, Cons(2, Empty()))

    A Union may be also be a partial by leaving one of its arguments
    Undefined:

      >>> partial = Union(Undefined, Cons(1, []))

    Calling partial unions will return the same object is no arguments are
    passed, or a performed union:

      >>> partial() is partial
      True

      >>> partial(Cons(2, []))
      Cons(2, Cons(1, Empty()))

    '''
    def __init__(self, xs=Undefined, ys=Undefined):
        self.xs = xs
        self.ys = ys

    def __repr__(self):
        return 'Union(%r, %r)' % (self.xs, self.ys)

    def __call__(self, *args):
        if self.xs is Undefined and args:
            xs, args = args[0], args[1:]
        else:
            xs = self.xs
        if self.ys is Undefined and args:
            ys, args = args[0], args[1:]
        else:
            ys = self.ys
        assert not args, 'Too many arguments'
        if xs is Undefined or ys is Undefined:
            if xs is self.xs and ys is self.ys:
                return self  # stop recursion in __new__
            else:
                return Union(xs, ys)
        elif isinstance(xs, Empty):
            return ys() if isinstance(ys, Union) else ys
        else:
            x, xs = xs
            return Cons(x, Union(xs, ys)())

    def __iter__(self):
        if self.xs is Undefined or self.ys is Undefined:
            raise TypeError('Partial union is not iterable')
        else:
            return self().iter()


class Intersection(Type):
    # Does not need to be a Type since we can cast Intersection as the monad
    # comprehension::
    #
    #    [x for x in a for y in b if x == y]
    #
    # However we may find a use for this when translating.
    #
    # NOTICE, as with most of this types is quite slow and not recommended to
    # be actually executed.  A couple of small lists of 15 elements can take a
    # lot of time to compute.
    def __init__(self, a=Undefined, b=Undefined):
        self.a = a
        self.b = b

    def __call__(self, *args):
        # ∩ :: S -> S -> S
        # [] ∩ b = []
        # a ∩ [] = []
        # (x: xs) ∩ (x: ys) = (x : xs ∩ ys)
        # (x: xs) ∩ (y: ys) = (xs ∩ (y: ys)) U ((x: xs) ∩ ys)
        a, b = self.a, self.b
        if a is Undefined and args:
            a, args = args[0], args[1:]
        if b is Undefined and args:
            b, args = args[0], args[1:]
        assert not args, 'Too many arguments'
        if a is Undefined or b is Undefined:
            return self
        elif isinstance(a, Empty) or isinstance(b, Empty):
            return Empty()
        else:
            x, xs = a
            y, ys = b
            if x == y:
                return Cons(x, Intersection(xs, ys)())
            else:
                return Union(
                    Intersection(xs, b)(),
                    Intersection(a, ys)()
                )()


# Monadic contructors
Zero = Empty
Unit = Cons(Undefined, Empty())


class _Mapper:
    # Simply wraps the function of a map, so that the original function is not
    # just a closure-accessible value, but exposed to the query translators.
    def __init__(self, f):
        self.f = f

    def __call__(self, x, xs):
        return Cons(self.f(x), xs)


# map f xs = foldr (λx, xs. f(x) : xs) [] xs
Map = lambda f: Foldr(_Mapper(f), Empty())
Join = Foldr(Union, Empty())

_orders = {
    '<': operator.lt,
    '<=': operator.le,
    '>': operator.gt,
    '>=': operator.ge,
}


class SortedCons(Type):
    '''The sorted insertion operation.

    :param order: The ordering function.  It may be one of the strings '<',
           '<=', '>', '>=' or any callable that accepts two arguments `x`, `y`
           and returns True if `x` is in the right order with regards to `y`.

           For instance, `operator.lt`:func: is a valid argument -- in fact,
           '<' is just an alias for it.

    '''
    def __init__(self, order, x=Undefined, xs=Undefined):
        if not callable(order):
            self.order = _orders[order]
        else:
            self.order = order
        self.x = x
        self.xs = xs

    def __iter__(self):
        def _iter():
            yield self.x
            yield self.xs
        if self.x is not Undefined and self.xs is not Undefined:
            return _iter()
        else:
            raise TypeError('SortedCons as a partial function cannot '
                            'be iterated')

    def __call__(self, *args):
        x, xs = self.x, self.xs
        if x is Undefined and args:
            x, args = args[0], args[1:]
        if xs is Undefined and args:
            xs, args = args[0], args[1:]
        assert not args
        if x is Undefined or xs is Undefined:
            return SortedCons(self.order, x, xs)
        elif isinstance(xs, Empty):
            return Cons(x, [])
        else:
            y, ys = xs
            if self.order(x, y):
                return Cons(x, Cons(y, ys)())
            else:
                return Cons(y, SortedCons(self.order, x, ys)())


Min = Foldr(lambda x, y: x if x < y else y, Infinity)
Max = Foldr(lambda x, y: x if x > y else y, -Infinity)
Sum = lambda s, initial=0: Foldr(lambda x, y: x + y, initial, s)
All = Foldr(operator.and_, True)
Any = Foldr(operator.or_, False)


def translate(source_tree, map='Map', unit='Unit', join='Join', zero='Empty'):
    '''Translate a `source tree` (`~xotl.ql.revenge.qst`:mod:) to an AST of
    function calls.

    This is the MC algorithm explained in [QLFunc]_.  It's kind of a
    denotational semantics of the comprehension sysntax in the sense it
    assigns meaning (function call) to every comprehesion expression.

    The function behaves as the following equations::

      MC [e | ]                     =  Unit(MC e)
      MC [e | x1, x2, ..., xn <- q] =  map (λx1, x2, ..., xn. MC e)(MC q)
      MC [e | p ]                   =  if MC p then (MC [e| ]) else Zero()
      MC [e | q, p]                 =  join(MC [MC [e| p]| q])
      MC e                          =  e   # other cases

    This function returns a *program* encoded in an AST of the function calls
    with the names provided in arguments `map`, `zero`, `unit`, and `join`.
    Also the ``X if C else Y``.

    This means this function *translates* the QST another program that is only
    composed of function calls (except for the last rule, which we explain
    later).  When you *evaluate* the program, you must provide actual
    callables for each name::

      eval(translate(qst), dict(map=Map, ...))

    .. warning:: You *should generate* the functions names in a way they don't
       collide with QST provide names.

    You must provide values for each function name `map`, `unit`, `zero`, and
    `join`.  They must be type-compatible for the program to work.  A simple
    (demonstration-only) set of functions is `Map`:func:, `Join`:func: ,
    `Zero`:func:, and `Unit`:func: defined in this module.  But you can
    provide different, yet similar ones.  Another viable set of functions may
    be::

      options = dict(
        Map=lambda f: lambda q: iter(f(x) for x in execute_plan(q)),
        Join=lambda lls: iter(x for l in lls for x in l),
        Unit=lambda x: iter([x]),
        Zero=lambda: iter([])
      )

    Notice there's some recursion because `map` calls `execute_plan` which is
    function that takes executes the translation that leads to `q`.  You can
    imagine it as equivalent to ``eval(translate(q), **options)()``.

    '''

    def Call(f, a=None):
        from xotl.ql import qst
        if a:
            return qst.Call(f, [a], [])
        else:
            return qst.Call(f, [], [])

    class generator:
        def __init__(self, target, iter):
            self.target = target
            self.iter = iter

    class genexpr:
        def __init__(self, elt, *exprs):
            self.elt = elt
            self.exprs = exprs

        @classmethod
        def from_qst(cls, qst):
            elt = qst.elt
            exprs = []
            for gen in qst.generators:
                exprs.append(generator(gen.target, gen.iter))
                exprs.extend(gen.ifs)
            return cls(elt, *exprs)

    def _build_lambda(target, body):
        if isinstance(target, qst.pyast.Name):
            params = [target.id]
        else:
            assert isinstance(target, qst.pyast.Tuple)
            params = [t.id for t in target.elts]
        return qst.Lambda(
            _make_arguments(*params),
            body
        )

    def _mc_routine(node):
        if isinstance(node, qst.pyast.GeneratorExp):
            return _mc_routine(genexpr.from_qst(node))
        elif isinstance(node, genexpr):
            elt = node.elt
            exprs = node.exprs
            if not exprs:
                # MC [e | ] -> Unit(MC e)
                return Call(
                    qst.Name(unit, qst.Load()),
                    _mc_routine(elt)
                )
            else:
                if len(exprs) > 1:
                    # MC [e | q, p] = join(MC [MC [e|p] | q])
                    q, p = exprs[:-1], exprs[-1]
                    return Call(
                        qst.Name(join, qst.Load()),
                        _mc_routine(
                            genexpr(_mc_routine(genexpr(elt, p)), *q)
                        )
                    )
                else:
                    g = exprs[0]
                    if isinstance(g, generator):
                        # MC [e | x <- q]  = map (λx. MC e) (MC q)
                        return Call(
                            Call(
                                qst.Name(map, qst.Load()),
                                _build_lambda(g.target, elt)
                            ),
                            _mc_routine(g.iter)
                        )
                    else:
                        # MC [e | p]  = if MC p then MC [e | ] else Empty()
                        else_ = Call(qst.Name(zero, qst.Load()))
                        then_ = _mc_routine(genexpr(elt))
                        cond_ = _mc_routine(g)
                        return qst.IfExp(cond_, then_, else_)
        elif isinstance(node, (list, tuple)):
            cls = type(node)
            return cls(_mc_routine(item) for item in node)
        elif isinstance(node, (qst.pyast.Name, qst.pyast.Num, qst.pyast.Str,
                               qst.pyast.Ellipsis, qst.pyast.boolop,
                               qst.pyast.operator, qst.pyast.unaryop,
                               qst.pyast.cmpop, qst.pyast.expr_context)):
            return node
        elif isinstance(node, qst.pyast.AST):
            # TODO: Walk inside other structures that may contain a
            # comprehension.
            fields = node._fields
            cls = type(node)
            res = cls()
            for field in fields:
                setattr(res, field, _mc_routine(getattr(node, field)))
            return res
        elif node is None:
            return None
        elif isinstance(node, builtins_types):
            return node
        else:
            assert False

    return qst.ensure_compilable(_mc_routine(source_tree))


# The Monad Compiler.
mcompile = translate


def _make_arguments(*names):
    from xotl.ql import qst
    if _py3:
        if _py_version >= (3, 4):
            return qst.arguments(
                [qst.arg(name, None) for name in names],
                None, [], [], None, []
            )
        else:
            return qst.arguments(
                [qst.arg(name, None) for name in names],
                None, None, [], None, None, [], []
            )
    else:
        return qst.arguments(
            [qst.Name(name, qst.Param()) for name in names],
            None, None, []
        )


from xoutil.eight import string_types, integer_types, class_types, binary_type
builtins_types = string_types + integer_types + class_types + (binary_type, )

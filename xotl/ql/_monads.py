#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# ---------------------------------------------------------------------
# _monads
# ---------------------------------------------------------------------
# Copyright (c) 2015 Merchise Autrement and Contributors
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the LICENCE attached (see LICENCE file) in the distribution
# package.
#
# Created on 2015-10-15

'''Monads comprehensions as a intermediate query language representation.

As noted in [QLFunc]_ algebra operators are an "abstraction of the algorithms
implemented by target query engines."  Therefore, the following implementation
of such operators are not designed to provide an efficient representation of
those algorithms and data structures.

The purpose of this is module is two-fold:

a) Provide an intermediate language for queries.

b) Provide a basic (testable) implementation of the intermediate language.

In this algebra the query ``(x for x in this if predicate(x))`` would be
represented as::

   Join(Map(lambda x: Unit(x) if predicate(x) else Empty())(this))

'''

from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)

from xoutil import Undefined


class Type(object):
    'An algebra as a type.'
    pass


class Empty(Type):
    '''Any empty collection.

    As a special case Undefined is considered an empty collection.

    '''
    def __new__(cls):
        '''Create the singleton instance of Empty.

        The following are always True::

          >>> Empty() is Empty()
          True

          >>> isinstance(Empty(), Empty)
          True

        '''
        instance = getattr(cls, 'instance', None)
        if instance is None:
            res = super(Empty, cls).__new__(cls)
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


class Cons(Type):
    r'''The collection constructor "x : xs".

    The basic usage is::

       >>> Cons(1, [])
       Cons(1, Empty())

    That builds the collection with a single element, the `Empty()` being the
    empty collection.

    You may also let any its arguments Undefined and that will create a
    partial::

        >>> from xoutil import Undefined
        >>> A1 = Cons(1, Undefined)

        >>> A1
        Cons(1)

        >>> A1(Cons(2, []))
        Cons(1, Cons(2, Empty()))

    You may extract the head and tail for non-partials Cons::

        >>> head, tail = A1([])

        >>> head, tail
        (1, Empty())

        >>> head, tail = A1
        Traceback

    '''
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
            x = args[0]
            args = args[1:]
        if xs is Undefined and args:
            xs = args[0]
            args = args[1:]
        assert not args
        return Cons(x, xs)

    def __iter__(self):
        def _iter():
            yield self.x
            yield self.xs
        if self.x is not Undefined:
            return _iter()
        else:
            raise TypeError('Cons as a partial function cannot be iterated')

    def asiter(self):
        assert self.xs is not Undefined and self.x is not Undefined
        head, tail = self
        yield head
        while not isinstance(tail, Empty):
            head, tail = tail
            yield head

    def aslist(self):
        return list(self.asiter())

    def asset(self):
        return set(self.asiter())

    def __repr__(self):
        if self.xs is not Undefined:
            return 'Cons(%r, %r)' % (self.x, self.xs)
        else:
            return 'Cons(%r)' % self.x


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
        if Undefined in (operator, arg, collection):
            return Foldr(operator, arg, collection)
        if isinstance(collection, Empty):
            return arg
        else:
            x, xs = collection
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
            l, args = args[0], args[1:]
        else:
            l = Undefined
        return (operator, z, l, args)


class Operation(Type):
    def __init__(self, operator, *partials):
        self.operator = operator
        self.partials = partials

    def __call__(self, *args):
        # if args:
        #     last = args[-1]
        args = self.partials + args
        print('%r%r' % (self.operator, args))
        return self.operator(*args)


class Union(Type):
    '''The Union operation.

    Unions are defined over `Cons`:class: instances.  Unions instances are
    callables that perform the union when called.

    Creating a Union::

      >>> whole = Union(Cons(1, []), Cons(2, []))
      >>> whole
      Union(Cons(1, Empty()), Cons(2, Empty()))

    Calling the union instance performs the union::

      >>> whole()
      Cons(1, Cons(2, Empty()))

    A Union may be also be a partial by leaving one of its arguments
    Undefined::

      >>> partial = Union(Undefined, Cons(1, []))

    Calling partial unions will return the same object is no arguments are
    passed, or a performed union.

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
        raise TypeError('Partial union is not iterable')


# Monadic contructors
Zero = Empty
Unit = Cons(Undefined, Empty())


class _Mapper(object):
    # Simply wraps the function of a map, so that the original function is not
    # just a closure-accessible value, but exposed to the query translators.
    def __init__(self, f):
        self.f = f

    def __call__(self, x, xs):
        return Cons(self.f(x), xs)


Map = lambda f: Foldr(_Mapper(f), Empty())
Join = Foldr(Union, Empty())


# Translation from comprehension syntax to monadic constructors
#
# MC [e | ]       ≝ Unit(MC e)
# MC [e | x <- q] ≝ map (λx. MC e) (MC q)
# MC [e | p ]     ≝ if MC p then MC e else Zero()
# MC [e | q, p]   ≝ join(MC [MC [e | p] | q])
# MC e            ≝ e   # other cases

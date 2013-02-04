#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#----------------------------------------------------------------------
# xotl.ql.expressions
#----------------------------------------------------------------------
# Copyright (c) 2012 Merchise Autrement and Contributors
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under
# the terms of the LICENCE attached in the distribution package.
#
# Created on May 24, 2012

'''
This module provides the building blocks for query expressions.

This module provides several classes that represent the operations themselves,
this classes does not attempt to provide anything else than what it's deem
needed to have an Abstract Syntax Tree (AST).
'''

from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        unicode_literals as _py3_unicode)

import operator
from functools import partial

from xoutil.context import context
from xoutil.aop import complementor
from xoutil.proxy import proxify, UNPROXIFING_CONTEXT, unboxed

from zope.interface import implements, directlyProvides

from xotl.ql.interfaces import (IOperator, IExpressionTree,
                                ISyntacticallyReversibleOperation,
                                ISynctacticallyCommutativeOperation)


__docstring_format__ = 'rst'
__author__ = 'manu'


class UNARY(object):
    @classmethod
    def formatter(cls, operation, children, kw=None):
        str_format = operation._format
        child = children[0]
        return str_format.format(str(child) if not isinstance(child,
                                                          ExpressionTree)
                                        else '(%s)' % child)


class BINARY(object):
    @classmethod
    def formatter(cls, operation, children, kw=None):
        str_format = operation._format
        child1, child2 = children[:2]
        return str_format.format(str(child1) if not isinstance(child1,
                                                          ExpressionTree)
                                        else '(%s)' % child1,
                            str(child2) if not isinstance(child2,
                                                          ExpressionTree)
                                        else '(%s)' % child2)


class N_ARITY(object):
    '''
    The arity of operations with a variable number or arguments::

        >>> class print_(FunctorOperator):
        ...    _format = 'print({0})'
        ...    arity = N_ARITY

        >>> print_()            # doctest: +ELLIPSIS
        <expression 'print()' ...>

        >>> print_(1, 2)        # doctest: +ELLIPSIS
        <expression 'print(1, 2)' ...>
    '''
    @classmethod
    def formatter(cls, operation, children, kwargs=None):
        str_format = operation._format
        args = ', '.join((str(child) if not isinstance(child,
                                                          ExpressionTree)
                                        else '(%s)' % child)
                         for child in children)
        if '{1}' in str_format:
            kwargs = {} if kwargs is None else kwargs
            if kwargs:
                kwargs = ", " + ', '.join("%s=%s" % (k, v)
                                          for k, v in kwargs.items())
                return str_format.format(args, kwargs)
            else:
                return str_format.format(args, '')
        else:
            return str_format.format(args)


class _boolean(type):
    def __invert__(self):
        """The `~` operator for custom booleans::

            >>> ~_true is _false
            True

            >>> ~_false is _true
            True

        """
        return _true if self is _false else _false

    def __and__(self, other):
        '''
            >>> (_true & 1) is 1
            True

            >>> (_false & 3) is _false
            True
        '''
        if self is _true:
            return other
        else:
            return self
    __rand__ = __and__

    def __or__(self, other):
        '''
            >>> (_true | 1) is _true
            True

            >>> (_false | 3) is 3
            True
        '''
        if self is _false:
            return other
        else:
            return self
    __ror__ = __or__


class _true(object):
    __metaclass__ = _boolean


class _false(object):
    __metaclass__ = _boolean


class OperatorType(type):
    '''The type of operators in an expression.'''

    operators = []

    def __init__(self, name, bases, attrs):
        from xoutil.objects import nameof
        OperatorType.operators.append(self)
        _PROVIDES = ('This {which} directly provides '
                     ':class:`xotl.ql.interfaces.{interface}`.\n\n')
        doc = ''
        for attr, trans in (('arity', nameof), ('_method_name', repr),
                            ('_format', repr)):
            value = getattr(self, attr, None)
            if value:
                v = trans(value).replace('_', r'\_')
                doc += ('\n\n    - **{attr}:** {v}'.format(attr=attr,
                                                           v=v))
        if doc:
            self.__doc__ = ((self.__doc__ if self.__doc__ else '') +
                            '\n\n    **Attributes**:' + doc)
        doc = ''
        interfaces = (IOperator, )
        if getattr(self, '_rmethod_name', False):
            interfaces += (ISyntacticallyReversibleOperation, )
            if 'ISyntacticallyReversibleOperation' not in self.__doc__:
                doc += _PROVIDES.format(
                            which='class',
                            interface='ISyntacticallyReversibleOperation')
        if getattr(self, 'equivalence_test', False):
            interfaces += (ISynctacticallyCommutativeOperation, )
            if 'ISynctacticallyCommutativeOperation' not in self.__doc__:
                doc += _PROVIDES.format(
                            which='class',
                            interface='ISynctacticallyCommutativeOperation')
        if doc:
            self.__doc__ += '\n\n    **Interface(s)**:\n\n' + doc

        directlyProvides(self, *interfaces)

    def __call__(self, *children, **named):
        '''Support for operators classes return expression trees upon
        "instantiation"::

            >>> class X(Operator): pass
            >>> isinstance(X(1, 2, 3), ExpressionTree)
            True

        '''
        return ExpressionTree(self, *children, **named)

    @property
    def method_name(self):
        '''
        The name of the method that is called to get the result of the
        operation.

        Python has a several protocols to invoke method in-place of operators
        in expressions. See the `Python's data model
        <http://doc.python.org/reference/datamodel.html>` for more information.

        This is the name of the method that is invoked by Python when the
        operation is found in a expression.

        See also :class:`FunctorOperator` for more information.
        '''
        return self._method_name


class Operator(object):
    '''
    The base class of every operation that may involved in a expression.

    Subclasses of this class are *rarely* instantiated, instead they are used
    in :attr:`ExpressionTree.operation` to indicate the operation that is
    perform to the :attr:`operands <ExpressionTree.children>`.

    '''
    __metaclass__ = OperatorType


class _FunctorOperatorType(OperatorType):
    '''
    A metaclass for :class:`FunctorOperator`.

    This provides operators that are called as functions with a dual behavior
    upon instantiation. To allow operands to customize how to place
    themselves in the operation, the "protocol" of calling the operand's
    method is implemented here, but if the operand just wants to build the
    `op(self, *others)` expression, we stack the first operand to avoid
    infinite recursion.

    This means that if you have an `opfunction` class that inherits from
    :class:`FunctorOperator` (or otherwise is an instance of this metaclass),
    when you call: ``opfunction(arg1, arg2, ...)``; will check if `arg1` has
    implemented the method in `_method_name` if so, we then call
    ``arg1._method_name(arg2, ...)``. If `arg1` just returns
    ``opfunction(self, arg2, ...)``, we stop recursing a provide the standard
    implementation: creating an expression of the type `(opfunction, *args)`.
    '''
    def __call__(self, *children, **named):
        if children:
            stack = context
            head, tail = children[0], children[1:]
            name = getattr(self, '_method_name', None)
            method = getattr(unboxed(head), name, None) if name else None
            if method and not stack[(head, method)]:
                func = getattr(method, 'im_func', method)
                with stack((head, method)):
                    if tail:
                        return func(head, *tail, **named)
                    else:
                        return func(head)
            else:
                return super(_FunctorOperatorType, self).__call__(*children,
                                                                  **named)
        else:
            return super(_FunctorOperatorType, self).__call__(*children,
                                                              **named)


class FunctorOperator(Operator):
    '''
    The base class for operations that are invoked explicitly by the
    programmer.

    Some operations like (:class:`count`, :class:`is_a`, etc.) are not called
    implicitly by Python and you must use them as "functions". So any
    customization you make to an object's method for the expression are not
    invoked by Python implicitly as it does for other operators.

    For instance, if you write a class `X` that defines both a `__add__` and
    `count` methods, when an expression ``instance_of_X + y`` is parsed, Python
    will call the `__add__` method and you may customize the way expressions
    are done for object of type `X`. But when ``count(instance_of_X)`` is
    parsed Python won't call the `count` method of `X`.

    This class adds such behavior. Operations that are always invoked
    explicitly by the programmer instead of Python's implicit invocation
    protocol, **should** inherit from this class. We take steps to prevent
    infinity recursion if an operand implements a protocol but calls the
    operator to build the final expression.
    '''
    __metaclass__ = _FunctorOperatorType


class BinaryCommutativeOperatorMixin(object):
    '''
    Mixin for *syntactically* commutative operators.

    Both the `==` and the `!=` operators are *always* commutative: i.e:
    `a == b` if and only if `b == a` no matter the types/domain of `a` and
    `b`.

    That's why Python does not have neither a `__req__` nor a `__rne__`
    protocols to implement the "reverse" of `__eq__` and `__ne__`.

    This mixin allows that we can compare for (syntactical) equivalence of
    `==` and `!=` in expressions::

        >>> e1 = 1 == q("2")
        >>> e2 = "2" == q(1)
        >>> with context(UNPROXIFING_CONTEXT):
        ...    e1 == e2
        True

    This is useful because the first expressions gets inverted cause `int`
    doesn't implement the `==` with q-objects::

        >>> e1                                        # doctest: +ELLIPSIS
        <expression '2 == 1' ...>
    '''
    arity = BINARY

    @staticmethod
    def equivalence_test(children1, children2):
        res = children1 == children2
        return res or (children1 == tuple(reversed(children2)))


class EqualityOperator(Operator, BinaryCommutativeOperatorMixin):
    '''
    The class of a == b [== c], expressions::

        >>> e = and_(eq(1, 2), eq(4, 5))
        >>> str(e)
        '(1 == 2) and (4 == 5)'

    '''
    _format = '{0} == {1}'
    _method_name = b'__eq__'
    _python_operator = operator.eq
eq = EqualityOperator


class NotEqualOperator(Operator, BinaryCommutativeOperatorMixin):
    '''
    The expression `a != b`::

        >>> e = ne(ne(1, 2), ne(4, 5))
        >>> str(e)
        '(1 != 2) != (4 != 5)'

    '''
    _format = '{0} != {1}'
    _method_name = b'__ne__'
    _python_operator = operator.ne
ne = NotEqualOperator


class LogicalAndOperator(Operator):
    '''
    The expression `a & b [& c]`::

        >>> e = and_(and_(1, 2), and_(4, 5))
        >>> str(e)
        '(1 and 2) and (4 and 5)'

    '''
    _format = '{0} and {1}'
    arity = BINARY
    _method_name = b'__and__'
    _rmethod_name = b'__rand__'
    _python_operator = operator.and_
and_ = LogicalAndOperator


class LogicalOrOperator(Operator):
    '''
    The expression `a or b [or c]`::

        >>> e = or_(or_(1, 2), or_(4, 5))
        >>> str(e)
        '(1 or 2) or (4 or 5)'

    '''
    _format = '{0} or {1}'
    arity = BINARY
    _method_name = b'__or__'
    _rmethod_name = b'__ror__'
    _python_operator = operator.or_
or_ = LogicalOrOperator


class LogicalXorOperator(Operator):
    '''
    The expression `a xor b [xor c]`::

        >>> e = xor_(xor_(1, 2), xor_(3, 4))
        >>> str(e)
        '(1 xor 2) xor (3 xor 4)'

    '''
    _format = '{0} xor {1}'
    arity = BINARY
    _method_name = b'__xor__'
    _rmethod_name = b'__rxor__'
    _python_operator = operator.xor
xor_ = LogicalXorOperator


class LogicalNotOperator(Operator):
    '''
    The logical `!a` expression::

        >>> e = not_(and_(1, 2))
        >>> str(e)
        'not (1 and 2)'

    '''
    _format = 'not {0}'
    arity = UNARY
    _method_name = b'__invert__'
    _python_operator = operator.invert
invert = not_ = LogicalNotOperator


class AdditionOperator(Operator):
    '''
    The expression `a + b [+ c]`::

        >>> e = add(add(1, 2), add(3, 4))
        >>> str(e)
        '(1 + 2) + (3 + 4)'

    '''
    _format = '{0} + {1}'
    arity = BINARY
    _method_name = b'__add__'
    _rmethod_name = b'__radd__'
    _python_operator = operator.add
add = AdditionOperator


class SubstractionOperator(Operator):
    '''The expression `a - b`.'''
    _format = '{0} - {1}'
    arity = BINARY
    _method_name = b'__sub__'
    _rmethod_name = b'__rsub__'
    _python_operator = operator.sub
sub = SubstractionOperator


class DivisionOperator(Operator):
    '''The expression `a / b`.'''
    _format = '{0} / {1}'
    arity = BINARY
    _method_name = b'__div__'
    _rmethod_name = b'__rdiv__'
    _python_operator = operator.div
truediv = div = DivisionOperator


class MultiplicationOperator(Operator):
    '''
    The expression `a * b [* c]`::

        >>> e = mul(mul(1, 2), mul(3, 4))
        >>> str(e)
        '(1 * 2) * (3 * 4)'

    '''
    _format = '{0} * {1}'
    arity = BINARY
    _method_name = b'__mul__'
    _rmethod_name = b'__rmul__'
    _python_operator = operator.mul
mul = MultiplicationOperator


class LesserThanOperator(Operator):
    '''
    The expression `a < b [< c]`::

        >>> e = and_(lt(1, 2), lt(3, 4))
        >>> str(e)
        '(1 < 2) and (3 < 4)'

    '''
    _format = '{0} < {1}'
    arity = BINARY
    _method_name = b'__lt__'
    _python_operator = operator.lt
lt = LesserThanOperator


class LesserOrEqualThanOperator(Operator):
    '''
    The expression `a <= b [<= c]`::

        >>> e = le(le(1, 2), le(3, 4))
        >>> str(e)
        '(1 <= 2) <= (3 <= 4)'

    '''
    _format = '{0} <= {1}'
    _associative = True
    arity = BINARY
    _method_name = b'__le__'
    _python_operator = operator.le
le = LesserOrEqualThanOperator


class GreaterThanOperator(Operator):
    '''
    The expression `a > b [> c]`::

        >>> e = gt(gt(1, 2), gt(3, 4))
        >>> str(e)
        '(1 > 2) > (3 > 4)'

    '''
    _format = '{0} > {1}'
    _associative = True
    arity = BINARY
    _method_name = b'__gt__'
    _python_operator = operator.gt
gt = GreaterThanOperator


class GreaterOrEqualThanOperator(Operator):
    '''
    The expression `a >= b [>= c]`::

        >>> e = ge(ge(1, 2), ge(3, 4))
        >>> str(e)
        '(1 >= 2) >= (3 >= 4)'

    '''
    _format = '{0} >= {1}'
    _associative = True
    arity = BINARY
    _method_name = b'__ge__'
    _python_operator = operator.ge
ge = GreaterOrEqualThanOperator


class ContainsExpressionOperator(FunctorOperator):
    '''
    The `b contains a` expression::

        >>> e = contains(('abc', 'abcdef'), 'abc')
        >>> print(str(e))
        contains(('abc', 'abcdef'), abc)

    '''
    _format = 'contains({0}, {1})'
    arity = BINARY
    _method_name = b'_contains_'
contains = ContainsExpressionOperator


class IsInstanceOperator(FunctorOperator):
    '''
    The `a is_a B` operator::

         >>> e = is_a(1, int)
         >>> str(e)
         "is_a(1, <type 'int'>)"

    '''
    _format = 'is_a({0}, {1})'
    arity = BINARY
    _method_name = b'_is_a'
is_a = is_instance = IsInstanceOperator


class FloorDivOperator(Operator):
    '''
    The `1 // 2` operator where `//` is always the floordiv operator::

        >>> e = floordiv(4, 3)
        >>> str(e)
        '4 // 3'

    '''
    _format = '{0} // {1}'
    arity = BINARY
    _method_name = b'__floordiv__'
    _rmethod_name = b'__rfloordiv__'
    _python_operator = operator.floordiv
floordiv = FloorDivOperator


class ModOperator(Operator):
    '''
    The `1 % 2` operator::

        >>> e = mod(4, 3)
        >>> str(e)
        '4 mod 3'

    '''
    _format = '{0} mod {1}'
    arity = BINARY
    _method_name = b'__mod__'
    _rmethod_name = b'__rmod__'
    _python_operator = operator.mod
mod = ModOperator


class PowOperator(Operator):
    '''
    The `1**2` operator::

        >>> e = pow_(4, 3)
        >>> str(e)
        '4**3'

    '''
    _format = '{0}**{1}'
    arity = BINARY
    _method_name = b'__pow__'
    _rmethod_name = b'__rpow__'
    _python_operator = operator.pow
pow_ = PowOperator


class LeftShiftOperator(Operator):
    '''
    The `2 << 1` operator::

        >>> e = lshift(2, 1)
        >>> str(e)
        '2 << 1'
    '''
    _format = '{0} << {1}'
    arity = BINARY
    _method_name = b'__lshift__'
    _rmethod_name = b'__rlshift__'
    _python_operator = operator.lshift
lshift = LeftShiftOperator


class RightShiftOperator(Operator):
    '''
    The `2 >> 1` operator::

        >>> e = rshift(2, 1)
        >>> str(e)
        '2 >> 1'
    '''
    _format = '{0} >> {1}'
    arity = BINARY
    _method_name = b'__rshift__'
    _rmethod_name = b'__rrshift__'
    _python_operator = operator.rshift
rshift = RightShiftOperator


class LengthFunction(FunctorOperator):
    '''The `length(something)` operator::

        >>> e = length(487873)
        >>> str(e)
        'length(487873)'

    .. note::

       :class:`length` is intended to be applied to non-collection values that
       have kind of a magnitude, like strings. It's not intended to be applied
       to collection of objects; use :class:`count` for those cases.

       :term:`Translators <query translator>` may rely on this rule to infer
       the type of the argument passed to either :class:`!length` or
       :class:`!count`.

    '''
    _format = 'length({0})'
    arity = UNARY
    _method_name = b'length'
length = LengthFunction


class CountFunction(FunctorOperator):
    '''The `count(something)` operator::

        >>> e = count((4, 8, 7, 8, 73))
        >>> str(e)
        'count((4, 8, 7, 8, 73))'

    .. note::

       :class:`count` is intended to be applied to collections. It's not
       supposed to be applied to non-collection values like strings; use
       :class:`length` for those cases.

       :term:`Translators <query translator>` may rely on this rule to infer
       the type of the argument passed to either :class:`!length` or
       :class:`!count`.

    '''
    _format = 'count({0})'
    arity = UNARY
    _method_name = b'_count'
count = CountFunction


class PositiveUnaryOperator(Operator):
    '''
    The `+56` unary operator::

        >>> e = pos(34)
        >>> str(e)
        '+34'

    '''
    _format = '+{0}'
    arity = UNARY
    _method_name = b'__pos__'
    _python_operator = operator.pos
pos = PositiveUnaryOperator


class NegateUnaryOperator(Operator):
    '''
    The `-56` unary operator::

        >>> e = neg(34)
        >>> str(e)
        '-34'

    '''
    _format = '-{0}'
    arity = UNARY
    _method_name = b'__neg__'
    _python_operator = operator.neg
neg = NegateUnaryOperator


class AbsoluteValueUnaryFunction(Operator):
    '''
    The `abs(56)` unary operator::

        >>> e = abs_(neg(43))
        >>> str(e)
        'abs((-43))'

    '''
    _format = 'abs({0})'
    arity = UNARY
    _method_name = b'__abs__'
    _python_operator = abs
abs_ = AbsoluteValueUnaryFunction


class AllFunction(FunctorOperator):
    '''
    The representation of the `all` function.

    There are three possible interpretations/syntaxes for :func:`all_`:

    1. It takes an expression (probably a subquery) and returns true only if
       every object is true::

            >>> ages = [1, 2, 3, 4, 5]
            >>> expr = all_(age > 10 for age in ages)
            >>> str(expr)        # doctest: +ELLIPSIS
            'all(<generator object...>)'

    2. takes several objects and evaluates them all (no subqueries)::

            >>> ages = (1, 2, 3, 4, 5)
            >>> expr = all_(*ages)
            >>> str(expr)
            'all(1, 2, 3, 4, 5)'

    3. takes two arguments: the first is a "generator" (see the
       :mod:`xotl.ql.core` module) and the second a predicate::

            >>> from xotl.ql.core import this
            >>> expr = all_(this.children, this.age > 10)
            >>> str(expr)
            'all(this.children, this.age > 10)'

    .. warning::

       There's no way to syntactically (at the level on which one could do
       normally in Python) to distiguish the last two elements from each other;
       so translators may further restrict these interpretations.
    '''

    _format = 'all({0})'
    arity = N_ARITY
    _method_name = b'all_'
all_ = AllFunction


class AnyFunction(FunctorOperator):
    '''
    The representation of the `any` function. As with :class:`all_` three
    analogous interpretations are possible. For instance::

        >>> ages = [1, 2, 3, 4, 5]
        >>> expr = any_(age > 10 for age in ages)
        >>> str(expr)        # doctest: +ELLIPSIS
        'any(<generator object...>)'
    '''

    _format = 'any({0})'
    arity = N_ARITY
    _method_name = b'any_'
any_ = AnyFunction


class MinFunction(FunctorOperator):
    '''
    A function that takes an expression and represents the minimun of such
    values over the collection.

    There are two possible syntaxes/interpretations for :func:`min_`:

    - A single argument is passed which represents a collection::

            >>> age = [1, 2, 3, 4, 5]
            >>> min_(age)        # doctest: +ELLIPSIS
            <expression 'min([1, 2, 3, 4, 5])' ...>

      This syntax allows complex expressions like::

            >>> from xotl.ql.core import this
            >>> min_(child.age for child in this) > 5    # doctest: +ELLIPSIS
            <expression '(min(...)) > 5' ...>

    - Several arguments are passed and the minimum of all is returned::

            >>> min_(1, 2, 3, 4, 5)    # doctest: +ELLIPSIS
            <expression 'min(1, 2, 3, 4, 5)' ...>

    .. note::

       :term:`Translators <query translator>` may take the use of either
       :func:`min_` or :func:`max_` functions over a single argument as a hint
       to the type of the argument (in this case a collection of other stuff
       according to the first interpretation).

       Such an assumption *should* be noted in the documentation of the
       translator.

    '''

    _format = 'min({0})'
    arity = N_ARITY
    _method_name = b'min_'
min_ = MinFunction


class MaxFunction(FunctorOperator):
    '''
    A function that takes an expression and represents the maximum of such
    values over the collection.

    Like :func:`min_` there are two possible interpretations for :func:`max_`,
    they are analogous.

    '''

    _format = 'max({0})'
    arity = N_ARITY
    _method_name = b'max_'
max_ = MaxFunction


class InvokeFunction(FunctorOperator):
    '''A function to allow arbitary function calls to be placed inside
    expressions. It's up to you that such functions behave as expect since is
    unlikely that they can be :term:`translated <query translator>`. For
    instance::

        >>> ident = lambda who, **kw: who
        >>> expr = call(ident, 1, a=1, b=2)
        >>> str(expr)     # doctest: +ELLIPSIS
        'call(<function <lambda> ...>, 1, a=1, b=2)'

    '''
    _format = 'call({0}{1})'
    arity = N_ARITY
    _method_name = b'invoke'
invoke = call = InvokeFunction


class StartsWithOperator(FunctorOperator):
    '''
    The `startswith(string, prefix)` operator::

         >>> e = startswith(q('something'), 's')
         >>> str(e)
         "startswith('something', 's')"

    .. note::

       At risk, use :class:`call` as ``call(string.startswith, 'prefix')``
    '''
    _format = 'startswith({0!r}, {1!r})'
    arity = BINARY
    _method_name = b'startswith'
startswith = StartsWithOperator


class EndsWithOperator(FunctorOperator):
    '''
    The `endswith(string, suffix)` operator::

        >>> e = endswith(q('something'), 's')
        >>> str(e)
        "endswith('something', 's')"


    .. note::

       At risk, use :class:`call` as ``call(string.startswith, 'suffix')``
    '''
    _format = 'endswith({0!r}, {1!r})'
    arity = BINARY
    _method_name = b'endswith'
endswith = EndsWithOperator


class AverageFunction(FunctorOperator):
    '''
    The ``avg(*args)`` operation. There're two possible interpretations:

    - A single argument (a collection) is passed and the average for each
      element is computed::

        avg(person.age for person in this)

    - Several arguments are passed::

        avg(1, 2, 3, 5)
    '''
    arity = N_ARITY
    _format = 'avg({0})'
    _method_name = b'_avg'
avg = AverageFunction


class NewObjectFunction(FunctorOperator):
    '''
    The expression for building a new object.

       >>> new(object, a=1, b=2)          # doctest: +ELLIPSIS
       <expression 'new(<type 'object'>, a=1, b=2)' ...>
    '''
    arity = N_ARITY
    _format = 'new({0}{1})'
    _method_name = b'_newobject'
new = NewObjectFunction


# XXXX: Removed the auto-mutable feature of expressions. Expressions should be
# regarded as immutable.

#    Auto-mutating expressions was a bad idea conceived to resolve the
#    case of `this` in the context of comprehensions like::
#
#        >>> next(parent for parent in this
#        ...        if (parent.age > 20) & parent.children)
#
#    It was thougth that this would return the expression as modified by
#    the conditions placed. But after more cases were proposed this was
#    shown wrong; in adition the design was getting too ugly.
#
#    Idioms like::
#
#        # Fetch the ages of parents that have more than two children.
#        >>> fetch(parent.age for parent in this
#        ...           if length(parent.children) > 2)
#
#    Here there are two elements that are different:
#
#    - The SELECT data that we need
#    - The CONDITIONS upon that data.
#
#    Auto-mutating expressions could not express the SELECT part of this
#    example.
#
#    So there are two possible solutions:
#
#    - Make `this` instances have a `binding` property that *do*
#      automutate in the context of comprehensions.
#
#    - Make `These.__iter__` return another kind of object.
#
#    We're currently exploring the first option, since the second
#    requires another type of object, that behaves like These, but have:
#
#    - CONDITIONS
#    - ORDERING?
#    - OFFSET and LIMIT


def _build_unary_operator(operation):
    method_name = operation._method_name
    def method(self):
        with context(UNPROXIFING_CONTEXT):
            meth = getattr(self, '_super_%s' % method_name, None)
        if not meth:
            meth = partial(operation, self)
        return meth()
    method.__name__ = method_name
    return method


def _build_binary_operator(operation):
    method_name = operation._method_name
    def method(self, other):
        with context(UNPROXIFING_CONTEXT):
            meth = getattr(self, '_super_%s' % method_name, None)
        if not meth:
            meth = partial(operation, self)
        return meth(other)
    method.__name__ = method_name
    return method


def _build_rbinary_operator(operation):
    method_name = getattr(operation, '_rmethod_name', None)
    if method_name:
        def method(self, other):
            meth = partial(operation, other)
            return meth(self)
        method.__name__ = method_name
        return method


_expr_operations = {operation._method_name:
                    _build_unary_operator(operation)
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

ExpressionTreeOperations = type(b'ExpressionTreeOperations', (object,),
                                _expr_operations)


# The _target_ protocol for expressions.
def _extract_target(which):
    if context['FLEXIBLE_TARGET_PROTOCOL']:
        target = getattr(which, '_target_', lambda x: x)
    else:
        target = getattr(type(which), '_target_', lambda x: x)
    return target(which)


@complementor(ExpressionTreeOperations)
class ExpressionTree(object):
    '''A representation of an expression as an :term:`expression tree`.

    Each expression has an `op` attribute that *should* be a class derived
    from :class:`Operator`, and a `children` attribute that's a tuple of the
    operands of the expression.

    Some operators support *named_children*, for instance, the :class:`call
    <InvokeFunction>` function may be passed a variable number of positional
    arguments (children) and a variable number of keyword argument (named
    children).

    '''
    implements(IExpressionTree)

    __slots__ = ('_op', '_children', '_named_children')

    def __init__(self, operation, *children, **named_children):
        '''
        Creates an expression tree with operatiorn `operator`.

            >>> class X(object):
            ...    @classmethod
            ...    def _target_(cls, self):
            ...        return 123

            >>> add(X(), 1978)    # doctest: +ELLIPSIS
            <expression '123 + 1978' at 0x...>

        '''
        self._op = operation
        self._children = tuple(_extract_target(child) for child in children)
        self._named_children = {name: _extract_target(value)
                                for name, value in named_children.items()}

    @property
    def op(self):
        '''The operator class of this expression. It should be a subclass of
        :class:`Operator`'''
        return self._op
    operation = op

    @property
    def children(self):
        'A tuple that contains the operands involved in the expression.'
        return self._children[:]

    @property
    def named_children(self):
        'A dictionary that contains the named operands in the expression.'
        return dict(self._named_children)

    def __eq__(self, other):
        '''
        Allows to compare for equality when UNPROXIFING_CONTEXT is active::

            >>> expression = eq(10, 34)
            >>> str(expression == eq(10, 34))
            '(10 == 34) == (10 == 34)'

            >>> with context(UNPROXIFING_CONTEXT):
            ...    expression == eq(10, 34)
            True
        '''
        from operator import eq as builtin_eq
        if context[UNPROXIFING_CONTEXT]:
            if isinstance(other, ExpressionTree):
                if self.op == other.op:
                    test = getattr(self.op, 'equivalence_test',
                                   builtin_eq)
                    return (test(self.children, other.children) and
                            builtin_eq(self.named_children,
                                       other.named_children))
                else:
                    return False
        else:
            result = eq(self, other)
            return result

    def __str__(self):
        arity_class = self.op.arity
        formatter = getattr(arity_class, 'formatter', None)
        if formatter:
            return formatter(self.op, self.children, self.named_children)
        else:
            return super(ExpressionTree, self).__str__()

    def __repr__(self):
        return "<expression '%s' at 0x%x>" % (self, id(self))


def _build_op_class(name, methods_spec):
    def build_meth(func, binary=True):
        def binary_meth(self, other):
            return func(self, other)

        def unary_meth(self):
            return func(self)

        if binary:
            return binary_meth
        else:
            return unary_meth
    attrs = {method_name: build_meth(func, binary)
                for method_name, func, binary in methods_spec}
    return type(name, (object,), attrs)


@proxify
class q(object):
    '''A light-weight wrapper for objects in an expression::

        >>> print(repr(1 + q(1)))           # doctest: +ELLIPSIS
        <expression '1 + 1' at 0x...>

    `q` wrappers are quite transparent, meaning that they will proxy every
    supported operation to its wrapped object.

    `q`-objects are based upon the xoutil's module :mod:`proxy module
    <xoutil:xoutil.proxy>`; so you should read its documentation.

    `q`-objects add support for building expressions using the wrapped object.
    But `q`-objects get out of the way and do not insert them selves into the
    expressions they build. For instance::

        >>> age = q(b'age')
        >>> type(age) is q
        True

        >>> expr = age + q(10)
        >>> [type(child) for child in expr.children]
        [<type 'str'>, <type 'int'>]

    '''
    r = lambda f: lambda self, other: f(other, self)

    query_fragment = _build_op_class(b'query_fragment',
                                     (('__and__', and_, True),
                                      ('__or__', or_, True),
                                      ('__rand__', r(and_), True),
                                      ('__ror__', r(or_), True),
                                      ('__xor__', xor_, True),
                                      ('__rxor__', r(xor_), True)))

    comparable_for_equalitity = _build_op_class(b'comparable_for_equalitity',
                                                (('__eq__', eq, True),
                                                 ('__ne__', ne, True)))

    comparable = _build_op_class(b'comparable',
                                 (('__lt__', lt, True),
                                  ('__gt__', gt, True),
                                  ('__le__', le, True),
                                  ('__ge__', ge, True)))

    class string_like(object):
        def startswith(self, preffix):
            return startswith(self, preffix)

        def endswith(self, suffix):
            return endswith(self, suffix)

    number_like = _build_op_class(b'number_like',
                                  (('__add__', add, True),
                                   ('__radd__', r(add), True),
                                   ('__sub__', sub, True),
                                   ('__rsub__', r(sub), True),
                                   ('__mul__', mul, True),
                                   ('__rmul__', r(mul), True),
                                   ('__pow__', pow_, True),
                                   ('__rpow__', r(pow_), True),
                                   ('__floordiv__', floordiv, True),
                                   ('__rfloordiv__', r(floordiv), True),
                                   ('__mod__', mod, True),
                                   ('__rmod__', r(mod), True),
                                   ('__div__', div, True),
                                   ('__rdiv__', r(div), True),
                                   ('__truediv__', truediv, True),
                                   ('__rtruediv__', r(truediv), True),
                                   ('__lshift__', lshift, True),
                                   ('__rlshift__', r(lshift), True),
                                   ('__rshift__', rshift, True),
                                   ('__rrshift__', r(rshift), True),
                                   ('__pos__', pos, False),
                                   ('__abs__', abs_, False),
                                   ('__neg__', neg, False),
                                   ('__invert__', not_, False)))

    behaves = [query_fragment, comparable, comparable_for_equalitity,
               number_like, string_like]

    @classmethod
    def _target_(cls, self):
        'Supports the target protocol for expressions'
        with context(UNPROXIFING_CONTEXT):
            return self.target

    def __init__(self, target):
        self.target = target

    # Hack to have q-objects represented like its targets...
    def __repr__(self):
        with context(UNPROXIFING_CONTEXT):
            return repr(self.target)

    def __str__(self):
        with context(UNPROXIFING_CONTEXT):
            return str(self.target)

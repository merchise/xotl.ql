#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#----------------------------------------------------------------------
# xotl.ql.expressions
#----------------------------------------------------------------------
# Copyright (c) 2012 Merchise Autrement
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License (GPL) as published by the
# Free Software Foundation;  either version 2  of  the  License, or (at
# your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA 02110-1301, USA.
#
# Created on May 24, 2012

'''This module provides the building blocks for query expressions.

This module provides several classes that represent the operations themselves,
this classes does not attempt to provide anything else than what it's deem
needed to have an Abstract Syntax Tree (AST).

Each expression is represented by an instance of an ExpressionTree. An
expression tree has two core attributes:

- The :py:attr:`~ExpressionTree.op` attribute contains a reference to the any
  of the classes that derive from :class:`Operator`.

- The :py:attr:`~ExpressionTree.children` attribute always contains a tuple
  with objects to which the operation is applied.

Operation classes should have the following attributes:

- `_arity`, which can be any of :py:class:`AT_LEAST_TWO`, :py:class:`BINARY`,
  or :py:class:`UNARY`.

- `_format`, which should be a string that specifies how to format the
  operation when str is invoked to print the expression. The format should
  conform to the format mini-language as specified in Python's string module
  doc.

  For UNARY operations it will be passed a single positional argument. For
  BINARY two positional arguments will be passed. AT_LEAST_TWO are currently
  BINARY operations that should have a boolean `_associative` attribute. The
  `_format` attribute should contains the format for two operands. We will
  concat the result with or without parenthesis according to the truth value of
  `_associative`.

- `_associative`, as explained above.

- `_method_name`, should contain a string (not unicode unless you're sure) with
  the name of the method that is be invoked on the (first) operand of the
  expression when this operation is used.

  This attribute simply maps operations to methods. This allows us to make
  expressions "composable", since expression trees will always have a "default"
  implementation of those methods, that normaly just buils another expression
  tree with it's `op` set to the operation.

This module provides operations for several of the commonly used in expression:
arithmetical, testing for containment, and others. So, expression are
composable::

    >>> expr1 = eq(1, 2) & eq(2, 3)
    >>> str(expr1)
    '(1 == 2) and (2 == 3)'

.. note:: We use `&` for the `and` operation, and `|` for the `or` operation.
          The "real" interpretation of "and" and "or" is not given in this
          module, but is left to the "compilation" phase. They may be regarded
          as logical or bitwise operations as well.



Objects in expressions
----------------------

In order to have any kind of objects in expressions, we provide a very ligth-
weight transparent wrapper :py:class:`q`. This simple receives an object as
it's wrapped, and pass every attribute lookup to is wrapped object but also
implements the creation of expressions with the supported operations. The
expression above could be constructed like::

    >>> expr2 = (q(1) == q(2)) & (q(2) == q(3))
    >>> str(expr2)
    '(1 == 2) and (2 == 3)'


The class :py:class:`q` contains more detailed information.


Contexts of execution
---------------------

Since the default operations of Python are "trapped" to build other expressions
as shown with::

    >>> expr1 == expr2    # doctest: +ELLIPSIS
    <expression '...' at 0x...>

it's difficult to test whether or not two expressions are equivalent, meaning
only that they represent the same AST and not its semantics. We use the simple
contexts of execution provided by :py:mod:`!xoutil.context` to enter
"special" modes of execution in which we change the semantic of an operation.

Since, :py:class:`q` is based on :py:mod:`xoutil.proxy`, and it's
likely that expressions contains `q`-objects, we use the same context name, the
proxy uses for similar purposes, i.e, :class:`~xotl.ql.proxy.UNPROXIFING_CONTEXT`::

    >>> from xoutil.context import context
    >>> from xoutil.proxy import UNPROXIFING_CONTEXT
    >>> with context(UNPROXIFING_CONTEXT):
    ...    expr1 == expr2
    True

.. warning::

   We only provide implementations for `__eq__` and `__ne__`, other operations
   will *probably* (but not always) fail in this context::

        >>> with context(UNPROXIFING_CONTEXT):    # doctest: +ELLIPSIS
        ...    q(1) + q(2) + expr1
        Traceback (most recent call last):
            ...
        RuntimeError: ...

   Only use `==` or `!=` in this context!


The case for `q`-objects
------------------------

`q`-objects are just meant to provide a simple wrapper for objects that don't
support the operations of expressions directly. They are not meant to be used
everywhere. Notice that expressions support most common operations and their
"reverses", so sometimes `q`-objects are not required::

    >>> 1 + q(1)  # doctest: +ELLIPSIS
    <expression '1 + 1' at 0x...>

For the time being, we keep the q-objects and they allows to test our
expression language. But, in time, we may refactor this class out of this
module.


.. autoclass:: q
   :members:


Thougths on Query Languages
---------------------------

Expressions are the core for query languages and many of it's design decisions
are strongly biased for query languages needs. But they purpose is more
general. Notice that :py:class:`this objects <xotl.ql.these.These>` are
they way to specify the selected data in queries.

The ultimate goal of expressions is to be *compiled* into forms feasible to the
current database (either relational or not) management systems. For instance,
it would be desirable that on top of CouchDB_ (or Couchbase_) expressions would
be *translated* to Couch's views if possible.

There's a good article [Buneman]_ that describe several features of a UnQL
(Unstructured Query Language), that are of interest to this module. Another
article exposes the relation between NoSQL and SQL, and renames the former as
coSQL following the categorical tradition since NoSQL is *dual* to SQL
[Meijer2011]_ [Fokkinga2012]_.

In this article [Meijer2011]_, the authors only focused on key-value stores for
noSQL databases. Although they claim that:

    While we don’t often think of it this way, the RAM for storing
    object graphs is actually a key-value store where keys are
    addresses (l-values) and values are the data stored at some
    address in memory (r-values). Languages such as C# and Java
    make no distinction between r-values and l-values, unlike C or
    C++, where the distinction is explicit. In C, the pointer
    dereference operator ``\*p`` retrieves the value stored at address ``p`` in
    the implicit global store.

Just as LINQ does for C#, one of the goals of the expression language its to
allow the construction of "natural" or better, idiomatic queries. Here the term
idiomatic, it's best cast a the natural idiom for the Object Model Canonical
Form (OMCaF) we're developing in :py:mod:`xotl.models`.

But the expression language cannot express the whole of queries. Real queries
require of:

- The SELECTION part, that identifies the data we want to retrieve. Sometimes,
  this part also transforms the data.

- And the SOURCE, that identifies the datastore we want to query.

- Optionally, a FILTER may be given to only retrieve data that match a
  criterion.

In addition, we often find:

- ORDER instructions to retrieve data in a given orden.
- OFFSET and LIMIT bounds to retrieve just a portion of the data.

The natural fit for expressions is the FILTER part. But we can also use the
same underlying AST mechanism to:

- Express the SELECTION part: `this.age` is a valid expression but is also a
  valid selector, and `count(1) + 100` is also a valid transform-making
  selector and a well-formed expression::

      >>> count(1) + 100    # doctest: +ELLIPSIS
      <expression '(count(1)) + 100' at 0x...>

- Express the ORDER part. This can be done with unary operators::

      >>> (+q('age'), -count(q('children')))    # doctest: +ELLIPSIS
      (<expression '+age'...>, <expression '-(count(children))...>)

.. note::

    Since `this` objects may have schemas bound to them, it's possible to bias
    the compiled expression to a given target. In fact, `this` instances may
    have whole expressions as bindings (constrains) and the fact the it refers
    to a given *kind* of object (and that the given kind has a schema
    associated to it) it's merely eventual.


About the operations supported in expression
--------------------------------------------

Almost any operation is supported by expressions. :class:`ExpressionTree`
uses the known :ref:`python protocols <py:datamodel>` to allow the composition
of expressions using an natural (or idiomatic) form, so::

    expression <operator> object

are the *suggested* form for constructing expressions. Doing so, allows other
objects (see the :mod:`~xotl.ql.these` module for example) to engage
into expressions and keeps the feeling of naturality.

The ``<operator>`` can be any of the supported operations, i.e:

- All the arithmetical operations, except `pow(a, b, modulus)` with a non-None
  `modulus`, but `a ** b` **is** supported.

- The ``&``, ``|``, and ``^`` operations. This are proposed to replace the
  `and`, `or`, and `xor` logical operations; but it's true meaning is dependant
  of the *expression compiler*.

- All the comparation operations: ``<``, ``>``, ``<=``, ``>=``, ``==``, and
  ``!=``.

- The unary operators for ``abs``, ``+``, ``-``, and ``~``. We **don't**
  support ``len``.

- The operators for testing containment ``__contains__``.

.. autoclass:: OperatorType(type)
   :members:


.. autoclass:: Operator
   :members:


.. autoclass:: FunctorOperator
   :members:

.. autoclass:: ExpressionTree
   :members:


.. _CouchDB: http://apache.org/couchdb
.. _Couchbase: http://www.couchbase.com/


Implementation
--------------

'''

from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        unicode_literals as _py3_unicode)

from copy import deepcopy

from functools import partial

from xoutil.types import Unset
from xoutil.context import context
from xoutil.aop import complementor

from xoutil.proxy import proxify, UNPROXIFING_CONTEXT, unboxed


__docstring_format__ = 'rst'
__author__ = 'manu'


class UNARY(object):
    @classmethod
    def formatter(cls, operation, children):
        str_format = operation._format
        child = children[0]
        return str_format.format(str(child) if not isinstance(child,
                                                          ExpressionTree)
                                        else '(%s)' % child)



class BINARY(object):
    @classmethod
    def formatter(cls, operation, children):
        str_format = operation._format
        child1, child2 = children[:2]
        return str_format.format(str(child1) if not isinstance(child1,
                                                          ExpressionTree)
                                        else '(%s)' % child1,
                            str(child2) if not isinstance(child2,
                                                          ExpressionTree)
                                        else '(%s)' % child2)



class _boolean(type):
    def __invert__(self):
        """The `~` operator for custom booleans::

            >>> ~_true is _false
            True

            >>> ~_false is _true
            True

        """
        return _true if self is _false else _false


class _true(object):
    __metaclass__ = _boolean

    def __and__(self, other):
        return other

    __rand__ = __and__

    def __or__(self, other):
        return self

    __ror__ = __or__

    def __repr__(self):
        return "True"




class _false(object):
    __metaclass__ = _boolean

    def __and__(self, other):
        return self

    __rand__ = __and__

    def __or__(self, other):
        return other

    __ror__ = __or__

    def __repr__(self):
        return "False"



class OperatorType(type):
    '''The type of operators in an expression.'''

    operators = []

    def __init__(self, name, bases, attrs):
        type(self).operators.append(self)

    def __call__(self, *children):
        '''Support for operators classes return expression trees upon
        "instantiation"::

            >>> class X(Operator): pass
            >>> isinstance(X(1, 2, 3), ExpressionTree)
            True

        '''
        return ExpressionTree(self, *children)


    @property
    def method_name(self):
        '''
        The name of the method that is called to get the result of the
        operation.

        Python has a several protocols to invoke method in-place of operators
        in expressions. See the :ref:`Python's data model <py:datamodel>` for
        more information.

        This is the name of the method that is invoked by Python when the
        operation is found in a expression.

        See also :class:`FunctorOperator` for more information.
        '''
        return self._method_name



class Operator(object):
    '''
    The base class of every operation that may involved in a expression.

    Subclasses of this class are *rarely* instantiated, instead they are used
    in :attr:`ExpressionTree.op` to indicate the operation that is perform to
    the :attr:`operands <ExpressionTree.children>`.
    '''
    __metaclass__ = OperatorType



class _FunctorOperatorType(OperatorType):
    '''
    A meta class for :class:`FunctorOperator`.

    This provides operators that are function with a dual behavior upon
    instantiantion. To allow operands to customize how to place themselves in
    the operation, the "protocol" of calling the operand's method is
    implemented here, but if the operand just wants to build the `op(self,
    *others)` expression, we weave the first operand to avoid infinit
    recursion.
    '''
    def __call__(self, *children):
        head, tail = children[0], children[1:]
        method = getattr(unboxed(head), self._method_name, None)
        if method:
            from xoutil.aop.basic import weaved
            func = getattr(method, 'im_func', method)
            # We weave the head to remove the method temporarily to avoid
            # infinit recursion if that method invokes this class with itself
            # as a the first operand.
            #
            # Notice that weaved is not thread-safe, since it messes with
            # head.__class__. But expressions are not thread-safe either. We
            # think that a expression is probably a very volatile object that
            # is disposed shortly after it's use.
            with weaved(head, **{self._method_name: None}) as head:
                if tail:
                    return func(head, *tail)
                else:
                    return func(head)
        else:
            return super(_FunctorOperatorType, self).__call__(*children)



class FunctorOperator(Operator):
    '''
    The base class for operations that are invoked explictly by the programmer.

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
    explicitly by the programmer instead of Python's implicit invokation
    protocol, **should** inherit from this class. We take steps to prevent
    infinity recursion if an operand implements a protocol but calls the
    operator to build the final expression.
    '''
    __metaclass__ = _FunctorOperatorType



class EqualityOperator(Operator):
    '''
    The class of a == b [== c], expressions::

        >>> e = and_(eq(1, 2), eq(4, 5))
        >>> str(e)
        '(1 == 2) and (4 == 5)'

    '''
    _format = '{0} == {1}'
    _associative = True
    _arity = BINARY
    _method_name = b'__eq__'


eq = EqualityOperator



class NotEqualOperator(Operator):
    '''
    The expression `a != b`::

        >>> e = ne(ne(1, 2), ne(4, 5))
        >>> str(e)
        '(1 != 2) != (4 != 5)'

    '''
    _format = '{0} != {1}'
    _associative = True
    _arity = BINARY
    _method_name = b'__ne__'


ne = NotEqualOperator



class LogicalAndOperator(Operator):
    '''
    The expression `a & b [& c]`::

        >>> e = and_(and_(1, 2), and_(4, 5))
        >>> str(e)
        '(1 and 2) and (4 and 5)'

    '''
    _format = '{0} and {1}'
    _associative = True
    _arity = BINARY
    _method_name = b'__and__'

and_ = LogicalAndOperator


class LogicalOrOperator(Operator):
    '''
    The expression `a or b [or c]`::

        >>> e = or_(or_(1, 2), or_(4, 5))
        >>> str(e)
        '(1 or 2) or (4 or 5)'

    '''
    _format = '{0} or {1}'
    _associative = True
    _arity = BINARY
    _method_name = b'__or__'

or_ = LogicalOrOperator



class LogicalXorOperator(Operator):
    '''
    The expression `a xor b [xor c]`::

        >>> e = xor_(xor_(1, 2), xor_(3, 4))
        >>> str(e)
        '(1 xor 2) xor (3 xor 4)'

    '''
    _format = '{0} xor {1}'
    _associative = True
    _arity = BINARY
    _method_name = b'__xor__'

xor_ = LogicalXorOperator



class LogicalNotOperator(Operator):
    '''
    The logical `!a` expression::

        >>> e = not_(and_(1, 2))
        >>> str(e)
        'not (1 and 2)'

    '''
    _format = 'not {0}'
    _arity = UNARY
    _method_name = b'__invert__'


not_ = LogicalNotOperator



class AdditionOperator(Operator):
    '''
    The expression `a + b [+ c]`::

        >>> e = add(add(1, 2), add(3, 4))
        >>> str(e)
        '(1 + 2) + (3 + 4)'

    '''
    _format = '{0} + {1}'
    _associative = True
    _arity = BINARY
    _method_name = b'__add__'


add = AdditionOperator



class SubstractionOperator(Operator):
    '''The expression `a - b`.'''
    _format = '{0} - {1}'
    _arity = BINARY
    _method_name = b'__sub__'

sub = SubstractionOperator



class DivisionOperator(Operator):
    '''The expression `a / b`.'''
    _format = '{0} / {1}'
    _arity = BINARY
    _method_name = b'__div__'


truediv = div = DivisionOperator



class MultiplicationOperator(Operator):
    '''
    The expression `a * b [* c]`::

        >>> e = mul(mul(1, 2), mul(3, 4))
        >>> str(e)
        '(1 * 2) * (3 * 4)'

    '''
    _format = '{0} * {1}'
    _associative = True
    _arity = BINARY
    _method_name = b'__mul__'

mul = MultiplicationOperator



class LesserThanOperator(Operator):
    '''
    The expression `a < b [< c]`::

        >>> e = and_(lt(1, 2), lt(3, 4))
        >>> str(e)
        '(1 < 2) and (3 < 4)'

    '''
    _format = '{0} < {1}'
    _associative = True
    _arity = BINARY
    _method_name = b'__lt__'

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
    _arity = BINARY
    _method_name = b'__le__'


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
    _arity = BINARY
    _method_name = b'__gt__'

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
    _arity = BINARY
    _method_name = b'__ge__'


ge = GreaterOrEqualThanOperator


class InExpressionOperator(Operator):
    '''
    The `a in b` expression::

        >>> e = in_('abc', ('abc', 'abcdef'))
        >>> print(str(e))
        in(abc, ('abc', 'abcdef'))

    '''
    _format = 'in({0}, {1})'
    _arity = BINARY
    _method_name = b'__contains__'


in_ = InExpressionOperator



class IsInstanceOperator(FunctorOperator):
    '''
    The `a is_a B` operator::

         >>> e = is_a(1, 2)
         >>> str(e)
         'is_a(1, 2)'

    '''
    _format = 'is_a({0}, {1})'
    _arity = BINARY
    _method_name = b'_is_a'


is_a = is_instance = IsInstanceOperator



class StartsWithOperator(FunctorOperator):
    '''
    The `string.startswith(something)` operator::

         >>> e = startswith(q('something'), 's')
         >>> str(e)
         "startswith('something', 's')"

    '''
    _format = 'startswith({0!r}, {1!r})'
    _arity = BINARY
    _method_name = b'startswith'


startswith = StartsWithOperator


class EndsWithOperator(FunctorOperator):
    '''
    The `string.endswith(something)` operator::

        >>> e = endswith(q('something'), 's')
        >>> str(e)
        "endswith('something', 's')"

    '''
    _format = 'endswith({0!r}, {1!r})'
    _arity = BINARY
    _method_name = b'endswith'


endswith = EndsWithOperator



class FloorDivOperator(Operator):
    '''
    The `1 // 2` operator where `//` is always the floordiv operator::

        >>> e = floordiv(4, 3)
        >>> str(e)
        '4 // 3'

    '''
    _format = '{0} // {1}'
    _arity = BINARY
    _method_name = b'__floordiv__'


floordiv = FloorDivOperator



class ModOperator(Operator):
    '''
    The `1 % 2` operator::

        >>> e = mod(4, 3)
        >>> str(e)
        '4 mod 3'

    '''
    _format = '{0} mod {1}'
    _arity = BINARY
    _method_name = b'__mod__'


mod = ModOperator


class PowOperator(Operator):
    '''
    The `1**2` operator::

        >>> e = pow_(4, 3)
        >>> str(e)
        '4**3'

    '''
    _format = '{0}**{1}'
    _arity = BINARY
    _method_name = b'__pow__'


pow_ = PowOperator



class LengthFunction(FunctorOperator):
    '''
    The `length(something)` operator::

        >>> e = length(487873)
        >>> str(e)
        'length(487873)'

    :class:`length` is intended to be applied to non-collection values that
    have a magnitude, like strings. It's not intended to be applied to
    collection of objects; use :class:`count` for those cases.

    '''
    _format = 'length({0})'
    _arity = UNARY
    _method_name = b'length'


length = LengthFunction


class CountFunction(FunctorOperator):
    '''
    The `count(something)` operator::

        >>> e = count(487873)
        >>> str(e)
        'count(487873)'

    :class:`count` is intended to be applied to collections. It's not supposed
    to be applied to non-collection values like strings; use :class:`length`
    for those cases.
    '''
    _format = 'count({0})'
    _arity = UNARY
    _method_name = b'count'


count = CountFunction



class PositiveUnaryOperator(Operator):
    '''
    The `+56` unary operator::

        >>> e = pos(34)
        >>> str(e)
        '+34'

    '''
    _format = '+{0}'
    _arity = UNARY
    _method_name = b'__pos__'


pos = PositiveUnaryOperator



class NegateUnaryOperator(Operator):
    '''
    The `-56` unary operator::

        >>> e = neg(34)
        >>> str(e)
        '-34'

    '''
    _format = '-{0}'
    _arity = UNARY
    _method_name = b'__neg__'


neg = NegateUnaryOperator



class AbsoluteValueUnaryFunction(Operator):
    '''
    The `abs(56)` unary operator::

        >>> e = abs_(neg(43))
        >>> str(e)
        'abs((-43))'

    '''
    _format = 'abs({0})'
    _arity = UNARY
    _method_name = b'__abs__'


abs_ = AbsoluteValueUnaryFunction



class InvertUnaryOperator(Operator):
    '''
    The `~56` unary operator::

        >>> e = invert(34)
        >>> str(e)
        '~34'

    '''
    _format = '~{0}'
    _arity = UNARY
    _method_name = b'__invert__'


invert = InvertUnaryOperator


# TODO: Review any_ and all_
class AnyFunction(FunctorOperator):
    '''
    A function that takes in a generator and an expression that must be proven
    True for at least a single element of the generator::

        >>> age = [1, 2, 3, 4, 5]
        >>> expr = any_(q('locals.age'), q('locals.age') > 3)
        >>> str(expr)
        'any(locals.age, (locals.age > 3))'
    '''

    _format = 'any({0}, {1})'
    _arity = BINARY
    _method_name = b'any_'


any_ = AnyFunction



class AllFunction(FunctorOperator):
    '''
    A function that takes in a generator and an expression that must be proven
    True for every single element of the generator::

        >>> age = [1, 2, 3, 4, 5]
        >>> expr = all_(q('locals.age'), q('locals.age') > 1)
        >>> str(expr)
        'all(locals.age, (locals.age > 1))'
    '''

    _format = 'all({0}, {1})'
    _arity = BINARY
    _method_name = b'all_'


all_ = AllFunction


class MinFunction(FunctorOperator):
    '''
    A function that takes an expression and represents the minimun of such
    values over the collection::

        >>> age = [1, 2, 3, 4, 5]
        >>> expr = min_(q(age))
        >>> str(expr)
        'min([1, 2, 3, 4, 5])'
    '''

    _format = 'min({0})'
    _arity = UNARY
    _method_name = b'min_'


min_ = MinFunction


class MaxFunction(FunctorOperator):
    '''
    A function that takes an expression and represents the maximum of such
    values over the collection::

        >>> age = [1, 2, 3, 4, 5]
        >>> expr = max_(q(age))
        >>> str(expr)
        'max([1, 2, 3, 4, 5])'
    '''

    _format = 'max({0})'
    _arity = UNARY
    _method_name = b'max_'


max_ = MaxFunction



class InvokeFunction(FunctorOperator):
    '''
    A function to allow arbitary function calls to be placed inside
    expressions. It's up to you that such functions behave as expect since is
    unlikely anyone translate it::

        >>> ident = lambda who: who
        >>> expr = call(q(1), ident)
        >>> str(expr)     # doctest: +ELLIPSIS
        'call(1, <function <lambda> ...>)'
    '''
    _format = 'call({0}, {1})'
    _arity = BINARY
    _method_name = b'__call__'


invoke = call = InvokeFunction

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



_expr_operations = {operation._method_name:
                    _build_unary_operator(operation)
                 for operation in OperatorType.operators
                    if getattr(operation, '_arity', None) == UNARY}
_expr_operations.update({operation._method_name:
                        _build_binary_operator(operation)
                      for operation in OperatorType.operators
                        if getattr(operation, '_arity', None) is BINARY})
ExpressionTreeOperations = type(b'ExpressionTreeOperations', (object,),
                                _expr_operations)


@complementor(ExpressionTreeOperations)
class ExpressionTree(object):
    '''
    A representation of a expression.

    Each expression has an `op` attribute that *should* be a class derived
    from :class:`Operator`, and a `children` attribute that's a tuple of the
    operands of the expression.

    '''
    def __init__(self, op, *children):
        self._op = op
        self._children = tuple(child for child in children)

    @property
    def op(self):
        'The operator class of this expression.'
        return self._op


    @property
    def children(self):
        'The operands involved in the expression.'
        return self._children[:]


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
        if context[UNPROXIFING_CONTEXT]:
            if isinstance(other, ExpressionTree):
                from xoutil.objects import validate_attrs
                return validate_attrs(self, other, ('op', 'children'))
        else:
            result = eq(self, other)
            return result


    def __str__(self):
        arity_class = self.op._arity
        formatter = getattr(arity_class, 'formatter', None)
        if formatter:
            return formatter(self.op, self.children)
        else:
            return super(ExpressionTree, self).__str__()


    def __repr__(self):
        return "<expression '%s' at 0x%x>" % (self, id(self))



def _build_op_class(name, methods_spec):
    def build_meth(func, binary=True):
        def binary_meth(self, other):
            if isinstance(other, q):
                other = unboxed(other).target
            return func(unboxed(self).target, other)

        def unary_meth(self):
            return func(unboxed(self).target)

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

        >>> print(str(q('parent')))
        parent

    `q` wrappers are quite transparent, meaning, that they will proxy
    every supported operation to its wrapped object.

    `q`-objects are based upon xoutil's :mod:`proxy module
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
    query_fragment = _build_op_class(b'query_fragment',
                                     (('__and__', and_, True),
                                      ('__or__', or_, True),
                                      ('__rand__', and_, True),
                                      ('__ror__', or_, True)))

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
                                   ('__radd__', add, True),
                                   ('__sub__', sub, True),
                                   ('__rsub__', sub, True),
                                   ('__mul__', mul, True),
                                   ('__rmul__', mul, True),
                                   ('__pow__', pow_, True),
                                   ('__rpow__', pow, True),
                                   ('__floordiv__', floordiv, True),
                                   ('__rfloordiv__', floordiv, True),
                                   ('__mod__', mod, True),
                                   ('__rmod__', mod, True),
                                   ('__div__', div, True),
                                   ('__rdiv__', div, True),
                                   ('__truediv__', truediv, True),
                                   ('__rtruediv__', truediv, True),
                                   ('__pos__', pos, False),
                                   ('__abs__', abs_, False),
                                   ('__neg__', neg, False),
                                   ('__invert__', invert, False)))

    behaves = [query_fragment, comparable, comparable_for_equalitity,
               number_like, string_like]


    def __init__(self, target):
        self.target = target


    # Hack to have q-objects represented like its targets...
    def __repr__(self):
        with context(UNPROXIFING_CONTEXT):
            return repr(self.target)


    def __str__(self):
        with context(UNPROXIFING_CONTEXT):
            return str(self.target)


    def __deepcopy__(self, memo=Unset):
        if memo is Unset:
            memo = {}
        d = id(self)
        y = memo.get(d, Unset)
        if y is not Unset:
            return y
        with context(UNPROXIFING_CONTEXT):
            target = deepcopy(self.target, memo)
        return q(target)

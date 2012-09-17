.. module:: xotl.ql.expressions

.. _expression-lang:

========================
The Expressions Language
========================

This module provides the building blocks for query expressions.

This module provides several classes that represent the operations themselves,
this classes does not attempt to provide anything else than what it's deem
needed to have an Abstract Syntax Tree (AST).

Each expression is represented by an instance of an ExpressionTree. An
expression tree has two core attributes:

- The :attr:`~ExpressionTree.operation` attribute contains a reference to the
  any of the classes that derive from :class:`Operator`.

- The :attr:`~ExpressionTree.children` attribute always contains a tuple
  with objects to which the operation is applied.

Operation classes should have the following attributes:

- `_arity`, which can be any of :class:`N_ARITY`, :class:`BINARY`, or
  :class:`UNARY`.

- `_format`, which should be a string that specifies how to format the
  operation when str is invoked to print the expression. The format should
  conform to the format mini-language as specified in Python's string module
  doc.

  For UNARY operations it will be passed a single positional argument. For
  BINARY two positional arguments will be passed. N_ARITY is regarded as
  function on several arguments (passed one after the other separated by
  commas); `_format` should have a single positional argument that will be
  replaced by the list of arguments.

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
weight transparent wrapper :class:`q`. This simple receives an object as
it's wrapped, and pass every attribute lookup to is wrapped object but also
implements the creation of expressions with the supported operations. The
expression above could be constructed like::

    >>> expr2 = (q(1) == q(2)) & (q(2) == q(3))
    >>> str(expr2)
    '(1 == 2) and (2 == 3)'


The class :class:`q` contains more detailed information.


Contexts of execution
---------------------

Since the default operations of Python are "trapped" to build other expressions
as shown with::

    >>> expr1 == expr2    # doctest: +ELLIPSIS
    <expression '...' at 0x...>

it's difficult to test whether or not two expressions are equivalent, meaning
only that they represent the same AST and not its semantics. We use the simple
contexts of execution provided by :mod:`!xoutil.context` to enter "special"
modes of execution in which we change the semantic of an operation.

Since, :class:`q` is based on :mod:`!xoutil.proxy` we use the same context name
the proxy module uses for similar purposes, i.e, to enter a special context in
which operation don't create new expression but try to evaluate themselve; such
a context is the object :class:`~xotl.ql.proxy.UNPROXIFING_CONTEXT`::

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

   This class implements :class:`xotl.ql.interfaces.IExpressionCapable`.


About the operations supported in expression
--------------------------------------------

Almost any operation is supported by expressions. :class:`ExpressionTree`
uses the known :ref:`python protocols <py:datamodel>` to allow the composition
of expressions using an natural (or idiomatic) form, so::

    expression <operator> object

are the *suggested* form for constructing expressions. Doing so, allows other
objects (see the :mod:`~xotl.ql.core` module for example) to engage
into expressions and keeps the feeling of naturality.

The ``<operator>`` can be any of the supported operations, i.e:

- All the arithmetical operations, except `pow(a, b, modulus)` with a non-None
  `modulus`, but `a ** b` **is** supported.

- The ``&``, ``|``, and ``^`` operations. This are proposed to replace the
  `and`, `or`, and `xor` logical operations; but its true meaning is dependent
  of the :term:`expression translator <query translator>`.

- All the comparation operations: ``<``, ``>``, ``<=``, ``>=``, ``==``, and
  ``!=``.

- The unary operators for ``abs``, ``+``, ``-``, and ``~``. We **don't**
  support ``len``.

- The operators for testing containment ``__contains__``.

.. autoclass:: OperatorType(type)
   :members:

   Instances of this class should provide the interface
   :class:`xotl.ql.interfaces.IOperator`.


.. autoclass:: Operator
   :members:

   Classes derived from this class should provide directly the interface
   :class:`xotl.ql.interfaces.IOperator`.


.. autoclass:: FunctorOperator
   :members:

.. autoclass:: ExpressionTree
   :members: operation, children

   This class implements the interface
   :class:`xotl.ql.interfaces.IExpressionTree`.


Included operations
-------------------

.. autoclass:: EqualityOperator

.. autoclass:: eq

.. autoclass:: NotEqualOperator

.. autoclass:: ne

.. autoclass:: LogicalAndOperator

.. autoclass:: and_

.. autoclass:: LogicalOrOperator

.. autoclass:: or_

.. autoclass:: LogicalXorOperator

.. autoclass:: xor_

.. autoclass:: LogicalNotOperator

.. autoclass:: not_

.. autoclass:: invert

.. autoclass:: AdditionOperator

.. autoclass:: add

.. autoclass:: SubstractionOperator

.. autoclass:: sub

.. autoclass:: DivisionOperator

.. autoclass:: div

.. autoclass:: truediv

.. autoclass:: MultiplicationOperator

.. autoclass:: mul

.. autoclass:: LesserThanOperator

.. autoclass:: lt

.. autoclass:: LesserOrEqualThanOperator

.. autoclass:: le

.. autoclass:: GreaterThanOperator

.. autoclass:: gt

.. autoclass:: GreaterOrEqualThanOperator

.. autoclass:: ge

.. autoclass:: InExpressionOperator

.. autoclass:: in_

.. autoclass:: IsInstanceOperator

.. autoclass:: is_a

.. autoclass:: is_instance

.. autoclass:: StartsWithOperator

.. autoclass:: startswith

.. autoclass:: EndsWithOperator

.. autoclass:: endswith

.. autoclass:: FloorDivOperator

.. autoclass:: floordiv

.. autoclass:: ModOperator

.. autoclass:: mod

.. autoclass:: PowOperator

.. autoclass:: pow_

.. autoclass:: LeftShiftOperator

.. autoclass:: lshift

.. autoclass:: RightShiftOperator

.. autoclass:: rshift

.. autoclass:: LengthFunction

.. autoclass:: length

.. autoclass:: CountFunction

.. autoclass:: count

.. autoclass:: PositiveUnaryOperator

.. autoclass:: pos

.. autoclass:: NegateUnaryOperator

.. autoclass:: neg

.. autoclass:: AbsoluteValueUnaryFunction

.. autoclass:: abs

.. autoclass:: AllFunction

.. autoclass:: all_

.. autoclass:: AnyFunction

.. autoclass:: any_

.. autoclass:: MinFunction

.. autoclass:: min_

.. autoclass:: MaxFunction

.. autoclass:: max_

.. autoclass:: StringFormatFunction

.. autoclass:: strformat

.. autoclass:: InvokeFunction

.. autoclass:: call

.. autoclass:: invoke



.. _extending-expressions-lang:

Extending the expressions language
----------------------------------

The expression language may be extended by introducing new
:term:`function object operators <function object operator>`. For
instance, one may need an average function::

   >>> from xotl.ql.expressions import FunctorOperator
   >>> class AverageFunction(FunctorOperator):
   ...     '''
   ...     The ``avg(*args)`` operation.
   ...     '''
   ...     _format = 'avg({0})'
   ...     _arity = N_ARITY
   ...     _method_name = b'_avg'
   >>> avg = Average Function

Given such a definition, now the `avg` callable produces expressions::

  >>> avg(0, 1, 2, 3, 4)    # doctest: +ELLIPSIS
  <expression 'avg(0, 1, 2, 3, 4)' ...>

Furthermore, you can even customize the way the expression is built by
implementing the `_avg` method on some specially averaged object::

  >>> class ZeroObject(object):
  ...    def _avg(self, *others):
  ...        if others:
  ...            return avg(*others)
  ...        else:
  ...            from xotl.ql.expressions import q
  ...            return q(0)

  >>> zero = ZeroObject()
  >>> avg(zero, 1, 2, 3)     # doctest: +ELLIPSIS
  <expression 'avg(1, 2, 3)' ...>

  >>> avg(zero)
  '0'

.. module:: xotl.ql.expressions

.. testsetup::

   from xotl.ql.interfaces import ISyntacticallyReversibleOperation
   from xotl.ql.expressions import *

.. _expression-lang:

========================
The Expressions Language
========================

This module provides the building blocks for creating :term:`expression trees
<expression tree>`. It provides several classes that represent the operations
themselves, this classes does not attempt to provide anything else than what
it's deem needed to have an Abstract Syntax Tree (AST).

Each expression is represented by an instance of an :class:`ExpressionTree`. An
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

In order to have any kind of objects in expressions, we provide a very
ligth-weight transparent wrapper :class:`q`. This simple receives an object as
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

Since :class:`q` is based on :mod:`!xoutil.proxy` we use the same context name
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

For the time being, we keep the q-objects as they allows to test our expression
language. But, in time, we may refactor this class out of this module.


.. autoclass:: q
   :members:

   This class implements :class:`xotl.ql.interfaces.IExpressionCapable`.


.. _target-protocol:

The `_target_` protocol for expressions
---------------------------------------

Expression trees support a custom protocol for placing operands inside
expressions. If any operand's class implements a method `_target_` it will be
called with the operand as its unique argument, and use its result in place of
the operand:

.. doctest::

   >>> class X(object):
   ...    @classmethod
   ...    def _target_(cls, self):
   ...        return 1

   >>> q(1) + X()  # doctest: +ELLIPSIS
   <expression '1 + 1' at 0x...>

This protocol will work with if `_target_` is either a method, a classmethod or
a staticmethod defined *in the class* object. It won't work if the `_target_`
method is injected into the instance:

.. doctest::

   >>> class X(object):
   ...     pass

   >>> def _target_(self):
   ...     return "invisible"

   >>> x = X()
   >>> setattr(x, '_target_', _target_)
   >>> q(1) + x   # doctest: +ELLIPSIS
   <expression '1 + <...X object at 0x...>' at 0x...>

.. todo::

   Do we really need this restriction? Wouldn't it be better to allow
   flexibility?

   I'm implementing a `FLEXIBLE_TARGET_PROTOCOL` execution context to testbed
   the lifting of this restriction:

   .. doctest::

      >>> from xoutil.context import context
      >>> with context('FLEXIBLE_TARGET_PROTOCOL'):    # doctest: +ELLIPSIS
      ...    q(20) + x
      <expression '20 + invisible' at 0x...>


   **Response**

   :class:`q` objects proxy all it attributes to the proxy target, so in those
   cases, working at the instance level may result in unpredictable results
   depending on whether the target has or not a _target_:

   .. doctest::

      >>> with context('FLEXIBLE_TARGET_PROTOCOL'):
      ...    expr = q('string') + q(1)

      >>> [type(x) for x in expr.children]  # doctest: +ELLIPSIS
      [<class '...q'>, <class '...q'>]

   Notice that the type of these objects is :class:`q` since they delegated the
   `_target_` protocol to their targets, and they don't implement the
   `_target_` protocol. At the class level, :class:`q` implements the
   `_target_` protocol with a `classmethod` and this would work as expected:

   .. doctest::

      >>> expr = q('string') + q(1)
      >>> [type(x) for x in expr.children]
      [<type 'str'>, <type 'int'>]


   That's probably why we should not work at the instance level.


Implementation via a metaclass also works:

.. doctest::

   >>> class MetaX(type):
   ...     def _target_(cls, self):
   ...         return 12

   >>> class X(object):
   ...     __metaclass__ = MetaX

   >>> q(1) + X()    # doctest: +ELLIPSIS
   <expression '1 + 12' at 0x...>

This is the protocol used by `q`-objects to get themselves out of expressions.


About the operations supported in expression
--------------------------------------------

Almost all normal operations are supported by
expressions. :class:`ExpressionTree` uses the known :ref:`python protocols
<py:datamodel>` to allow the composition of expressions using an natural
(idiomatic) form, so::

    expression <operator> object

are the *suggested* form for constructing expressions. Doing so, allows other
objects (see the :mod:`~xotl.ql.core` module for example) to engage
into expressions and keeps the feeling of naturality.

The ``<operator>`` can be any of the supported operations, i.e:

- All the arithmetical operations, except `pow(a, b, modulus)`, but `a ** b`
  **is** supported.

- The ``&``, ``|``, and ``^`` operations. This are proposed to replace the
  `and`, `or`, and `xor` logical operations; but its true meaning depends on
  the :term:`expression translator <query translator>`.

- All the comparison operations: ``<``, ``>``, ``<=``, ``>=``, ``==``, and
  ``!=``.

- The unary operators for ``abs``, ``+``, ``-``, and ``~``. We **don't**
  support ``len``. The ``~`` is proposed to encode the `not` logical operator;
  but its true meaning depends of the used query translator.

.. autoclass:: OperatorType(type)
   :members:

   This is the metaclass for the class :class:`Operator` it automatically
   injects documentation about
   :class:`xotl.ql.interfaces.ISyntacticallyReversibleOperation` and
   :class:`xotl.ql.interfaces.ISynctacticallyCommutativeOperation`, so there's
   no need to explicitly declare which interfaces the class support in every
   operator class.


.. autoclass:: Operator
   :members:

   Classes derived from this class should provide directly the interface
   :class:`xotl.ql.interfaces.IOperator`.


.. autoclass:: FunctorOperator
   :members:

.. autoclass:: ExpressionTree
   :members: operation, children, named_children

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

.. autoclass:: ContainsExpressionOperator

.. autoclass:: contains

.. warning:

   Despite we could use the `__contains__` protocol for testing containment,
   Python always convert the returned value to a bool and thus destroys the
   expression tree.

   If you need an expression that expresses a containment test, you **must**
   use the :class:`in_` operator like this::

       in_(item, collection)


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

.. autoclass:: abs_

.. autoclass:: AllFunction

.. autoclass:: all_

.. autoclass:: AnyFunction

.. autoclass:: any_

.. autoclass:: MinFunction

.. autoclass:: min_

.. autoclass:: MaxFunction

.. autoclass:: max_

.. autoclass:: InvokeFunction

.. autoclass:: call

.. autoclass:: invoke

.. autoclass:: AverageFunction

.. autoclass:: avg


.. _extending-expressions-lang:

Extending the expressions language
----------------------------------

The expression language may be extended by introducing new
:term:`function object operators <function object operator>`. For
instance, one may need an `sin` function::

   >>> from xotl.ql.expressions import FunctorOperator
   >>> class SinFunction(FunctorOperator):
   ...     '''
   ...     The ``sin(arg)`` operation.
   ...     '''
   ...     _format = 'sin({0})'
   ...     _arity = UNARY
   ...     _method_name = b'_sin'
   >>> sin = SinFunction

Given such a definition, now the `sin` callable produces expressions::

  >>> sin(0)    # doctest: +ELLIPSIS
  <expression 'sin(0)' ...>

Furthermore, you can even customize the way the expression is built by
implementing the `_sin` method on some special object::

  >>> class ZeroObject(object):
  ...    def _sin(self):
  ...        return sin(360)

  >>> zero = ZeroObject()
  >>> sin(zero)     # doctest: +ELLIPSIS
  <expression 'sin(360)' ...>

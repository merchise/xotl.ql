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

Each expression is represented by an instance of an
:class:`xotl.ql.expressions.ExpressionTree`. An expression tree has two core
attributes:

- The :attr:`~xotl.ql.expressions.ExpressionTree.operation` attribute contains
  a reference to the any of the classes that derive from :class:`Operator`.

- The :attr:`~xotl.ql.expressions.ExpressionTree.children` attribute always
  contains a tuple with objects to which the operation is applied.

Operation classes should have the following attributes:

- `_arity`, which can be any of :class:`xotl.ql.expressions.N_ARITY`,
:class:`xotl.ql.expressions.BINARY`, or :class:`xotl.ql.expressions.UNARY`.

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
ligth-weight transparent wrapper :class:`xotl.ql.expressions.q`. This simple
receives an object as it's wrapped, and pass every attribute lookup to is
wrapped object but also implements the creation of expressions with the
supported operations. The expression above could be constructed like::

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


.. autoclass:: xotl.ql.expressions.q
   :members:

   This class implements :class:`xotl.ql.interfaces.IExpressionCapable`.


.. _target-protocol:

The `_xotl_target_` protocol for expressions
--------------------------------------------

Expression trees support a custom protocol for placing operands inside
expressions. If any *operand's class* implements a method `_xotl_target_` it
will be called with the operand as its unique argument, and use its result in
place of the operand:

.. doctest::

   >>> class X(object):
   ...    @classmethod
   ...    def _xotl_target_(cls, self):
   ...        return 1

   >>> q(1) + X()  # doctest: +ELLIPSIS
   <expression '1 + 1' at 0x...>

.. note::

   This protocol only works if `_xotl_target_` is either an attribute (method,
   a classmethod or a staticmethod) defined **in the class** object (or its
   metaclass). It won't work if the `_xotl_target_` method is injected into the
   instance.

This is the protocol used by `q`-objects to get themselves out of expressions.


About the operations supported in expression
--------------------------------------------

Almost all normal operations are supported by expressions (please refer to the
:mod:`API for the expression language <xotl.ql.expressions>` for the complete
list of supported operations and
functions). :class:`xotl.ql.expressions.ExpressionTree` uses the known
:ref:`python protocols <py:datamodel>` to allow the composition of expressions
using an natural (idiomatic) form, so::

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

.. autoclass:: xotl.ql.expressions.OperatorType(type)
   :members:

   This is the metaclass for the class :class:`xotl.ql.expressions.Operator` it
   automatically injects documentation about
   :class:`xotl.ql.interfaces.ISyntacticallyReversibleOperation` and
   :class:`xotl.ql.interfaces.ISynctacticallyCommutativeOperation`, so there's
   no need to explicitly declare which interfaces the class support in every
   operator class.


.. autoclass:: xotl.ql.expressions.Operator
   :members:

   Classes derived from this class should provide directly the interface
   :class:`xotl.ql.interfaces.IOperator`.


.. autoclass:: xotl.ql.expressions.FunctorOperator
   :members:

.. autoclass:: xotl.ql.expressions.ExpressionTree
   :members: operation, children, named_children

   This class implements the interface
   :class:`xotl.ql.interfaces.IExpressionTree`.


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


.. _resolve-arguments-protocol:

The protocol for resolving ambiguous signatures
-----------------------------------------------

Functions like :class:`~xotl.ql.expressions.all_`
:class:`~xotl.ql.expressions.any_` could have several signatures, one of them
being a subquery-like expression. In order to have chance to process the
subquery if the operator implements the `_resolve_arguments` method (see
:class:`xotl.ql.expressions.ResolveSubQueryMixin`) it will be called before any
other processing is done to children (like the target protocol explained
before).

============================================================
:mod:`xotl.ql.expressions` - API for the expression language
============================================================


.. module:: xotl.ql.expressions

.. testsetup::

   from xotl.ql.interfaces import ISyntacticallyReversibleOperation
   from xotl.ql.expressions import *


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

.. autoclass:: NegativeUnaryOperator

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

.. autoclass:: NewObjectFunction

.. autoclass:: new


Resolving signatures like :class:`any_` does
============================================

.. autoclass:: ResolveSubQueryMixin
   :members: _resolve_arguments

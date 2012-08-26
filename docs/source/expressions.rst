.. _expression-lang:

========================
The Expressions Language
========================

.. automodule:: xotl.ql.expressions
   :members:


.. _extending-expressions-lang:

Extending the expressions language
==================================

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
  ...        return avg(*others)

  >>> zero = ZeroObject()
  >>> avg(zero, 1, 2, 3)     # doctest: +ELLIPSIS
  <expression 'avg(1, 2, 3)' ...>

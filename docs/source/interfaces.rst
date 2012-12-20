.. _api-ref:

=============
API reference
=============

.. module:: xotl.ql.interfaces

This documents list all the interfaces that altogether form the API of
`xotl.ql`.

External API
============

This part of the API is that must freeze when the first stable release of
`xotl.ql` is to be released.

Query objects interfaces
------------------------

:term:`Query objects <query object>` are represented by objects implementing
the :class:`IQueryObject` below.

.. autointerface:: IQueryObject
   :members: selection, tokens, filters, ordering, partition, params, __iter__, next

.. autointerface:: IGeneratorToken
   :members: expression

Expression language API
-----------------------

.. autointerface:: IExpressionCapable

.. autointerface:: IExpressionTree
   :members: operation, children, named_children

.. autointerface:: ITerm
   :members: name, parent, __iter__, __getattribute__

.. autointerface:: IBoundTerm
   :members: binding

.. autointerface:: IOperator
   :members: _format, arity, _method_name

.. autointerface:: ISyntacticallyReversibleOperation
   :members: _rmethod_name

.. autointerface:: ISynctacticallyCommutativeOperation
   :members: equivalence_test

Translation API
---------------

.. autointerface:: IQueryTranslator

.. autointerface:: IQueryExecutionPlan


Internal API
============

This section describes the internal interfaces used when processing
comprehensions in order to build the queries. Documenting this "internal" is
important because we feel will ease the understanding of how `xotl.ql` works.

.. autointerface:: IQueryPart
   :members: expression

.. autointerface:: IQueryParticlesBubble
   :members: capture_part, capture_token, parts, tokens, particles

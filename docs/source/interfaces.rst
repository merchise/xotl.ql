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
the :class:`IQuery` below.

.. autointerface:: IQuery
   :members: selection, tokens, filters, ordering, partition

.. autointerface:: IQueryTranslator

.. autointerface:: IQueryExecutionPlan

.. autointerface:: IGeneratorToken
   :members: token

.. autointerface:: IExpressionTree
   :members: operation, children, named_children

.. autointerface:: IExpressionCapable

.. autointerface:: IThese
   :members: name, parent, __iter__, __getattribute__

.. autointerface:: IOperator


Internal API
============

This section describes the internal interfaces used when processing
comprehensions in order to build the queries. Documenting this "internal" is
important because we feel will ease the understanding of how `xotl.ql` works.

.. autointerface:: IQueryPart
   :members: token, expression

.. autointerface:: IQueryPartContainer
   :members: created_query_part

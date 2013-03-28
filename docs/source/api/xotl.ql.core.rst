================================================
:mod:`xotl.ql.core` - API for the query language
================================================

.. module:: xotl.ql.core

External API for the query language
===================================

In this section we give the details of the (external) query API. For the
internal query API, used to those that need to build extensions of the query
language, please refer to :ref:`query-api`.

As we've said, at the core of the Query Language is the `this` object, whose
type is a subclass of the class :class:`Term`:

.. autodata:: this(name, **kwargs)


.. autoclass:: Term
   :members: name, parent, root_parent,  __iter__

   This class implements :class:`xotl.ql.interfaces.ITerm`

.. autoclass:: _QueryObjectType
   :members: build_from_generator

.. class:: these(generator, **kwargs)

   An alias to the :class:`QueryObject`, you may use either as a constructor
   for :term:`query objects <query object>`. However we use both names for
   different purposes:

   - We use :class:`these` with the `(generator, ...)` signature only to get a
     :term:`query object` from a :term:`query expression`.

   - We use :class:`QueryObject` without any arguments, to build a bare
     :term:`query object` that may be filled afterward.

     The only valid signature is the one of :class:`these`, any other signature
     will produce a `TypeError`.

   .. note::

      The metaclass :class:`_QueryObjectType` of :class:`these` hooks into the
      way of creating instances (:term:`query objects <query object>`), if you
      pass a single positional argument which is of type `GeneratorType` and
      possibly many others keyword arguments, the metaclass will use its
      :meth:`_QueryObjectType.build_from_generator` method.


.. autoclass:: QueryObject

.. autoclass:: GeneratorToken

Implementation Details
======================

.. autoclass:: QueryPart
   :members:

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
type is a subclass of the class :class:`Term` explained below:
v.. autodata:: this(name, **kwargs)

.. autoclass:: Term
   :members: name, parent, root_parent,  __iter__, clone

   This class implements :class:`xotl.ql.interfaces.ITerm`

.. class:: these(generator, **kwargs)

   An alias to the :class:`QueryObject`, you may use either as a constructor
   for :term:`query objects <query object>`. However we use both names for
   different purposes:

   - We use :class:`these` with the `(query expression, ...)` signature only to
     get a :term:`query object` from a :term:`query expression` in a style that
     looks like a function call.

   - We use :class:`QueryObject` without any arguments to build a bare
     :term:`query object` that may be filled afterward.

   .. note::

      When providing any arguments the only valid signature is the one showed
      in this page. If you pass any arguments, you *must* ensure that:

      - There is a **single** positional argument of type `GeneratorType`
      - Any other argument is a *keyword argument*.

      Any other signature raises a TypeError. See
      :meth:`_QueryObjectType.build_from_generator` for more.

.. autoclass:: QueryObject

.. autoclass:: GeneratorToken

.. autoclass:: _QueryObjectType
   :members: build_from_generator

===========================================================================
:mod:`xotl.ql.translation` - Common routines for translation and a test bed
===========================================================================

.. module:: xotl.ql.translation

This package comprises:

- Several utilities like :func:`cotraverse_expression` that are deemed general
  enough to serve the purposes of translation without regards of the target
  :term:`object model`; and

- A module :mod:`py` that contains the implementation of a :term:`query
  translator` that matches the Python's object model and selects objects in
  this space.


Common routines for translation
===============================

Traversing expressions
----------------------

The following function is thought to help out the task of traversing a filters
and yield those of interest for the translator (i.e finding the top-most
generator token that is related to a table in a relational model).

.. note:: Although we use the Python 3.2+ syntax in the signature, this
	  function works the same in Python 2.7.

.. autofunction:: cotraverse_expression(*expressions, accept=None)


Ordering of tokens, terms and expressions
-----------------------------------------

These functions are meant to help to know whether a filter needs to be executed
after a token or not.

Let's see a query::

    these(child
          for parent in this
          for child in parent.children
          if parent.age > 42
	  if child.age < 10)

In this case the filter over the age of the `parent` might be executed *before*
trying to even loop over its children. So a query translator might take this
fact into account to optimize the query plan.

The following functions are utilities to accomplish this.

.. warning:: The logic behinds those function actually establish a *partial*
	     order between in the domain of terms and expressions. But being
	     partial means that some of those object are not comparable under
	     this order.

	     Currently :func:`cmp` and :func:`cmp_terms` return ``0`` in the
	     case of non-comparable subjects. This fools Python's sorting
	     heuristics that consider that equality is transitive (ie. if
	     `a==b` and `b==c` then `a==c`) but this does not hold in this
	     case.

	     So *DON'T* use those functions neither as an argument to `sorted`,
	     `list.sort` or `functools.cmp_to_key` functions: you won't get the
	     expected results.

	     I don't know any Python's library that deals with partial orders
	     and implements a stable order algorithm. One may try to encode
	     this in a DAG and do a topological sorting, but I don't believe is
	     worthy since the amount of terms/expressions to be compared in a
	     query is quite small; and since query objects are deemed
	     inmutable, a cache from query objects to query plans is possible
	     to keep.

.. autofunction:: cmp_terms(term1, term2, strict=False)

.. autofunction:: token_before_filter

.. autofunction:: cmp

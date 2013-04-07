=============================================================================
:mod:`xotl.ql.translation` - Common routines for translation of query objects
=============================================================================

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

.. autofunction:: get_term_path

.. autofunction:: get_term_signature

.. autofunction:: cmp_terms(term1, term2, strict=False)

.. autofunction:: token_before_filter

.. autofunction:: cmp

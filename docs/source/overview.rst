.. _overview:

========
Overview
========

A running system often needs to retrieve objects from a single or several
sources.  Those sources are often databases, but that is by no means a
universal truth; for instance, in a distributed environments objects might
reside in other types of software components.

A query language assists programmers in the task of retrieving those objects
or, at least, get a handle to those objects (like a proxy to an object in a
distributed system [#querying]_.)

The main goal for `xotl.ql` is to provide a *pythonic way to write* queries.
In this regard, `xotl.ql` has a similar outlook that LINQ queries have in C#
[#these]_.

And now the query is just::

  >>> from xotl.ql import this
  >>> parents = (parent for parent in this if len(parent.children) > 2)

As you can see queries are just normal generator expressions (usually over the
:data:`~xotl.ql.core.this` object).  The previous query is readable as it
stands: get all the parents that have more than 2 children.

More complex queries are allowed, for instance::

  >>> parents = (parent
  ...            for parent in this
  ...            if parent.children and all(child.age > 10
  ...                                       for child in parent.children))

This would retrieve every "parent" whose children are all more than 10 years
old (assuming `age` is measured in years).

Up to this point, the only thing you have accomplish is to *write* a query.
We haven't told how to actually run the query.  The next section deals with
this matter.


.. _role-of-query-translator:

The role of the query language and query translators
====================================================

In the previous introduction, we have shown how the syntax of the query
language looks, and we have indicated the *intended meaning* of the
constructions.  However, `xotl.ql` does not enforce any particular
interpretation on the queries since the whole meaning of queries depends on
the semantics of the `object model`:term: in place.

For instance, given a data model that honors transitive relations such as "`is
(physically) located in`" between places; if you have that "`B is located in
A`" and that "`C is located in B`", then querying for every place that is
located in `A`, should return both `B` and `C`.

One might encode such a query in a program like the following::

  >>> locations = (place for place in this if place.located_in(A))

It's expected that such a query will look up in the all the containment tree
derived form the `located-in` relation, to fetch all places which are inside
`A` either directly or indirectly.

In this model, just the use of ``located_in(A)`` would imply a recursive
computation; and such knowledge comes only from the object/store model and not
the query language by itself.  Other models (for instance the relational model)
might not find more than directly related objects.

That's why in order to execute queries one *must* use a :term:`query
translator` with enough knowledge of the object model and of the system
configuration (specially how to communicate with the storage system).

`xotl.ql` won't provide production quality translators.  Instead other
packages will be released that implement translators and assist their
configuration into other frameworks.  For instance, it's planned to write a
package that contains a translator for SQLAlchemy_ models and another package
with a Pyramid_ Tween that glues this translator with Pyramid.

.. _SQLAlchemy: http://pypi.python.org/pypi/sqlalchemy
.. _Pyramid: http://pypi.python.org/pypi/pyramid

Nevertheless the module :mod:`xotl.ql.translation.py` does contains an
implementation of a translator that fetches objects from the Python's
memory.  And we also provide utilities for translation in
:mod:`xotl.ql.translation`.


Retrieving objects
==================

Assuming you have a translator, like the function
`~xotl.ql.translation.py.naive_translation`:func:, you may simply pass a query
to it to obtain a `query execution plan`:term:::

  >>> from xotl.ql.translation.py import naive_translation

  >>> query = naive_translation(parent for parent in this)


Query execution plans are iterable::

  >>> for which in query:
  ...    print(which)


A plan is required to be reusable, so that you run the same query more than
one time avoiding the translation phase.  This does not means that you will
always get the same results from the reused execution plan, since the
underlying data source might have changed.


See the document about `translators <translation>`:ref: for more information.


Footnotes
=========

.. [#querying] Querying objects in a distributed environment is a no-go for
	       performance issues.  However the language by itself is
	       possible.  One may maintain indexes for distributed systems,
	       though; and the queries are run against these indexes.

.. [#these] When we started this project we thought we could have queries
	    without having to call a function/class, just comprehensions and
	    the :data:`~xotl.ql.core.this` symbol.  Unfortunately, we have had
	    to add :class:`~xotl.ql.core.these` callable so that all pieces of
	    a query were properly captured.

	    If you are interested in the inner workings of `xotl.ql`, see
	    :ref:`inner-workings`.

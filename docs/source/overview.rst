.. _overview:

========
Overview
========

The main goal of `xotl.ql` is to provide a *facilities* that allow writing
queries in a *pythonic way*.  In this regard, `xotl.ql` has a similar outlook
that LINQ queries have in C#.

A `query expression`:term: takes the form of a Python generator expression::

  >>> from xotl.ql import this
  >>> parents = (parent for parent in this if len(parent.children) > 2)

The previous query is readable as it stands: get all the parents that have
more than 2 children.

More complex queries are allowed, for instance::

  >>> parents = (parent
  ...            for parent in this
  ...            if parent.children and all(child.age > 10 for child in parent.children))

This would retrieve every "parent" whose children are all more than 10 years
old (assuming `age` is measured in years).

Notice, however, that those interpretations of the queries match only our
intuitions about them, and `xotl.ql` does not enforce any particular meaning
to the query.  `xotl.ql` is all about *writing* queries having this particular
syntactical look.


.. _role-of-query-translator:

The role of the query language and query translators
====================================================

In the previous introduction, we have shown how the syntax of the query
language looks, and we have indicated the *intended meaning* of the
constructions.  However, `xotl.ql` does not enforce any particular
interpretation on the queries since the whole meaning of queries depends on
the semantics of the `object model`:term: in place.  For instance, given a
data model that honors transitive relations such as "`is (physically) located
in`" between places; if you have that "`B is located in A`" and that "`C is
located in B`", then querying for every place that is located in `A`, should
return both `B` and `C`.

One might encode such a query in a program like the following::

  >>> locations = (place for place in this if place in A)

It's expected that such a query will look up in the all the containment tree
derived form the `located-in` relation, to fetch all places which are inside
`A` either directly or indirectly.

In this model, the use of ``in A`` would imply a recursive computation; and
such knowledge comes only from the object/store model and not the query
language by itself.  Other models (for instance the relational model) might
not find more than directly related objects.

..
   A different approach would be to write the query as::

     >>> locations = (found for place in this if place is A and found in place)

   Though this construction would make no-sense in a Python only view of the
   world, it could make sense for a query language (and it may actually work!)

That's why in order to execute queries one *must* use a :term:`query
translator` with enough knowledge of the object model and of the system
configuration (specially how to communicate with the storage system).

`xotl.ql` won't provide production quality translators.  Instead, other
packages will be released that implement translators and assist their
configuration into other frameworks.  Nevertheless the module
:mod:`xotl.ql.translation.py` does contains an implementation of a translator
that fetches objects from the Python's memory.  And we also provide utilities
for translation in :mod:`xotl.ql.translation`.


Retrieving objects
==================

Assuming you have a translator, like `~xotl.ql.translation.py`:mod:, you may
simply pass a query to it to obtain a `query execution plan`:term:::

  >>> from xotl.ql.translation import py
  >>> query = py(parent for parent in this)


Query execution plans are iterable::

  >>> for which in query:          # doctest: +SKIP
  ...    print(which)


A plan is required to be reusable, so that you may run the same query more
than once and avoiding the translation phase.  This does not means that you
will always get the same results from the reused execution plan, since the
underlying data source might have changed.

See the document about `translators <translation>`:ref: for more information.


Query expressions v. query objects
==================================

So far we have seen how queries are expressed in our code.  A query as the
python expression we see in our code (or as the generator object it implies)
is more precisely referred as a `query expression`:term:.

On the other hand, translators need a data structure that describes the query.
Since we can't actually provide translators with the query expression (what we
see is a Python `generator`:ref: object), we need another object that
precisely capture the query.  This is the `query object`:term:.  In many
cases, the distinction between those terms is not important but for internal
documents is very important.  Translators will mostly deal with query objects.
Getting a query object from a query expression is what `xotl.ql` is supposed
to do well.

The function `xotl.ql.core.get_query_object`:func: takes a query expression
(i.e a generator object) and return a query object.

.. _overview:

========
Overview
========

A running system often needs to retrieve objects from a single or several
sources. Those sources are often databases, but that is by no means a universal
truth; for instance, in a distributed environments objects might reside in
other types of software components.

A query language assists programmers in the task of retrieving those objects
or, at least, get a handle to those objects (like a proxy to an object in a
distributed system [#querying]_.)

The main goal for `xotl.ql` is to provide a *pythonic way to write* queries. In
this regard, `xotl.ql` has a similar [#these]_ outlook that LINQ queries have
in C#.

The `xotl.ql` package comprises two main components: the :ref:`expression
language <expression-lang>` and the :ref:`query language <query-lang>` itself.

The expression language just allows to form expressions using common
operations.  The result of an expression is an :term:`expression tree`
object.

The expression language is :ref:`fairly extensible <extending-expressions-lang>`
as you may introduce new :term:`function object operators <function object
operator>`.

The query language relies heavily upon the expression language. The core of the
query language itself is just a combination of:

- Python's generator expressions that use the expression language ;

- the object :data:`~xotl.ql.core.this`; and

- the :class:`~xotl.ql.core.these` class.

Let's see a query. First let's import what we need::

  >>> from xotl.ql import this, these
  >>> from xotl.ql.expressions import count

And now the query is just::

  >>> parents = these(parent for parent in this if count(parent.children) > 2)

As you can see queries are just normal generator expressions (usually over the
:data:`~xotl.ql.core.this` object) wrapped inside the
:class:`~xotl.ql.core.these` function. The previous query is readable as it
stands: get all the parents that have more than 2 children.

More complex queries are allowed, for instance::

  >>> from xotl.ql.expressions import all_
  >>> parents = these(parent
  ...                 for parent in this
  ...                 if parent.children & all_(child.age > 10
  ...                                           for child in parent.children))

This would retrieve every "parent" whose children are all more than 10 years
old (assuming `age` is measured in years).

.. note::

   In the expression language, the logical operations `and`, `or`, and `not`
   are encoded using the operators "``&``", "``|``", and "``~``" respectively;
   but since in Python those are bit-wise operations they don't have the same
   priority the keywords do, so you might have to use parentheses:
   ``(count(this.children) > 0) & (count(this.children) < 4)``.

   You may use the function-like operators :class:`~xotl.ql.expressions.and_`,
   :class:`~xotl.ql.expressions.or_`, and :class:`~xotl.ql.expressions.not_` if
   you're not comfortable using the operators.

   Moreover you can't use the idiom ``a < b < c`` in expressions because Python
   converts such a construction to ``a < b and b < c`` and there's no way we
   can hook into `and`.

   For the same reason you can't use ``in``, and ``isinstance`` in
   expressions. Python always convert those expressions to boolean and this is
   not what we need in the context of the expression language.


.. _role-of-query-translator:

The role of the query language and query translators
====================================================

So far, we have shown how the syntax of the query language looks, and we have
indicated the *intended meaning* of the constructions. However, `xotl.ql` does
not enforce any particular interpretation on the queries since the whole
meaning of queries depends on the semantics of the objects models in place.

For instance, given a data model that honors transitive relations such as `is
(physically) located in` between places; if you have that `B is located in A`
and that `C is located in B`, then querying for every place that is located in
`A`, should return both `B` and `C`.

One might encode such a query in a program like the following::

  locations = these(place for place in this if place.located_in(A))

It's expected that such a query will look up in the all the containment tree
derived form the `located-in` relation, to fetch all places which are inside
`A` either directly or indirectly.

In this model, just the use of ``located_in(A)`` would imply a recursive
computation; and such knowledge comes only from the object/store model and not
the query language by itself. Other models (for instance the relational model)
might not find more than directly related objects.

That's why in order to execute queries one *must* use a :term:`query
translator` with enough knowledge of the object model and of the system
configuration (specially how to communicate with storage systems).

`xotl.ql` won't provide production quality translators. Instead other packages
will be released that implement translators and assist their configuration into
other frameworks. For instance, it's planned to write a package that contains a
translator for SQLAlchemy_ models and another package with a Pyramid_ Tween
that glues this translator with Pyramid.

.. _SQLAlchemy: http://pypi.python.org/pypi/sqlalchemy
.. _Pyramid: http://pypi.python.org/pypi/pyramid

Nevertheless the module :mod:`xotl.ql.translation.py` does contains an
implementation of a translator that fetches objects from the Python's
memory. And we also provide utilities for translation in
:mod:`xotl.ql.translation`.


Retrieving objects
------------------

If a query translator is :ref:`setup <translator-conf>`, then you may iterate
over the query itself to fetch objects::

  somequery = these(parent for parent in this)
  for parent in somequery:
      print(parent)

If no translator is configured an exception is raised. This allows to keep
things simple at the data-consuming level. However, this by no means the only
way to retrieve data from a query. You could use a translator directly instead
of using the "default" one. See more on :ref:`translation`.


Footnotes
=========

.. [#querying] Querying objects in a distributed environment is a no-go for
	       performance issues. However the language by itself is
	       possible. One may maintain indexes for distributed systems,
	       though; and the queries are run against these indexes.

.. [#these] When we started this project we thought we could have queries
	    without having to call a function/class, just comprehensions and
	    the :data:`~xotl.ql.core.this` symbol. Unfortunately, we have had
	    to add :class:`~xotl.ql.core.these` callable so that all pieces of
	    a query were properly captured.

	    If you are interested in the inner workings of `xotl.ql`, see
	    :ref:`inner-workings`.

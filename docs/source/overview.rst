.. _overview:

========
Overview
========

A running system often needs to retrieve objects from a single or several
sources. Those sources are often databases, but that is by no means a universal
truth; for instance, in distributed environments objects may reside in other
types of software components.

A query language assists programmers in the task of retrieving those objects or,
at least, get a handle to those objects (like a proxy to an object in a
distributed system [#querying]_.)

The `xotl.ql` package comprises two main components: the :ref:`expression
language <expression-lang>` and the :ref:`query language <query-lang>` itself.

The expression language just allows to form expressions using common operations.
The resultant "expressions" are actually python objects that represent the
:term:`expression tree`. As usual, the inner nodes of the expression tree
represents operations and the leaves have the operands.

The expression language is :ref:`fairly extensible <extending-expressions-lang>`
as you may introduce new :term:`function object operators <function object
operator>`.

The query language relies heavily upon the expression language, since it allows
to express predicates on the objects. The core of the query language itself is
just a combination of:

- the expression language used inside Python's generator expressions and/or
  dictionary comprehensions (we shall use the term :term:`comprehension` to
  refer both to generator expressions and dictionary comprehensions when it does
  not matter the difference);

- the :data:`~xotl.ql.core.this` object; and

- the :func:`~xotl.ql.core.these` function.

Let's see a query::

  >>> from xotl.ql import this, these
  >>> parents = these(parent for parent in this if parent.children)

As you can see queries are just normal python comprehensions (usually over the
:data:`~xotl.ql.this` object) wrapped inside the :func:`~xotl.ql.these`
function.

More complex queries are allowed, for instance::

  >>> from xotl.ql.expressions import all_
  >>> parents = these(parent for parent in this
  ...                    if parent.children &
  ...                       all_(child.age > 10 for child in parent.children))

This would retrieve every "parent" whose children are all more that 10 years
(supposedly).

.. warning::

   Logical operations `and`, `or`, and `not` are encoded using the operators:
   `&`, `|` and `~` respectively; but since in Python those are bit-wise
   operations they don't have the same priority as the keywords so you may have
   to use parentheses: ``(count(this.children) > 0) & (count(this.children) <
   4)``.

   Moreover you can't use the idiom `a < b < c` in query expressions because
   Python converts such a construction to `a < b and b < c` and there's no way
   we can hook into `and`.


Combining data from two or more "tables"
========================================

Although there is no such thing as a Table at the query language level, it is
possible to express join-like expression in `xotl.ql`. However,




Subqueries
==========

::

  >>> from xotl.ql.expressions import all_
  >>> parents = these(parent for parent in this
  ...                     if parent.children &
  ...                        all_(child.age > 10 for child in parent.children))



Unions
======

::

  >>> Article = type('Article', (object, ), {})
  >>> Book = type('Book', (object, ), {})
  >>> from xotl.ql.expressions import is_a
  >>> from xotl.ql.core import union, these
  >>> books = (book for book in this if is_a(book, Book))
  >>> articles = (article for article in this if is_a(book, Article))
  >>> docs = union(books, articles)


Executing queries
=================

So far, we have shown the syntax of the query language and we have indicated the
*intended meaning* of the constructions. However, `xotl.ql` does not enforce any
particular interpretation on the queries since the whole meaning of queries
depends on the semantics of the objects models in place.

For instance, in a model that honors "transitive" relations such as
`located-in`, saying that `B is located-in A` and that `C is located-in B`, then
the query::

  >>> inside_a = these(place for place in this if place.located_in.name == 'A')

may be expected to look up in the all the containment tree derived form the
`located-in` relation, to see all places which are inside `A` either directly or
indirectly. In this case, just by using the `located_in.name == 'A'` would imply
a recursive function; such a knowledge comes from the object model and not the
query language by itself; so:

   in order to execute queries one **must** provide a :term:`query translator`
   with enough knowledge of the object model and of the system configuration
   (specially how to communicate with storage systems).


Retrieving objects
------------------

If a query translator is setup and working, then you may use the built-in `next`
function to retrieve the objects that matches your query::

  >>> somequery = these(parent for parent in this)
  >>> next(somequery)    # doctest: +SKIP
  <SOME OBJECT>

If no translator is configured an exception is raised upon calling `next`.

Thougths on Query Languages
===========================

Expressions are the core for query languages and many of it's design decisions
are strongly biased for query languages needs. But they purpose is more
general. Notice that :class:`~xotl.ql.core.These` instances are they way to
specify the selected data in queries.

The ultimate goal of expressions is to be :term:`compiled <query execution
plan>` into forms feasible to the current database (either relational or not)
management systems. For instance, it would be desirable that on top of CouchDB_
(or Couchbase_) expressions would be *translated* to Couch's javascript views
if possible.

For instance a query like:

.. code-block:: python

   these(parent for parent in this if parent.age > 30)

may be translated to a view with the following `map` function:

.. code-block:: javascript

   function(doc) {
     if (doc.age > 30) {
       map.emit(doc._id, doc)
     }
   }

A query with a subquery like:

.. code-block:: python

   these(parent for parent in this
                if parent.children &
                   all_(child.age > 5 for child in parent.children))

may be translated cleverly straightforwardly if `children` is (as CouchDB
encourages for documents) is contained inside `parent`:

.. code-block:: javascript

   function (doc) {
     if (doc.children) {
       var _cond = function(c){return c.age > 5}
       var _i = 0;
       var _child = doc.children[_i];
       var _all = _cond(_child);
       var _l = doc.children.length();
       while(_all and _i < _l) {
         _i++;
	 _child = doc.children[_i];
	 _all = _cond(_child);
       }
       if (_all) {
         map.emit(doc._id, doc)
       }
     }
   }

If `children` is not contained in `parent` such kind of translation is not be
possible, so the :term:`query translator` might use several views and integrate
it's results with Python code.

There's a good article [Buneman]_ that describe several features of a UnQL
(Unstructured Query Language), that are of interest to this module. Another
article exposes the relation between NoSQL and SQL, and renames the former as
coSQL following the categorical tradition since NoSQL is *dual* to SQL
[Meijer2011]_ [Fokkinga2012]_.

In this article [Meijer2011]_, the authors only focused on key-value stores for
noSQL databases. Although they claim that:

    While we don’t often think of it this way, the RAM for storing object
    graphs is actually a key-value store where keys are addresses (l-values)
    and values are the data stored at some address in memory
    (r-values). Languages such as C# and Java make no distinction between
    r-values and l-values, unlike C or C++, where the distinction is
    explicit. In C, the pointer dereference operator ``*p`` retrieves the value
    stored at address ``p`` in the implicit global store.

Just as LINQ does for C#, one of the goals of the expression language its to
allow the construction of natural or idiomatic queries. Here the term
idiomatic, it's best cast a the natural idiom for the Object Model Canonical
Form (OMCaF) we're developing in :mod:`xotl.models`.

.. _CouchDB: http://apache.org/couchdb
.. _Couchbase: http://www.couchbase.com/

Footnotes
=========

.. [#querying] Querying objects in a distributed environment is a no-go for
	       performance issues. However the language by itself is possible.

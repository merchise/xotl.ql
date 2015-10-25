.. _query-lang:

=============================================
The query language and the `this`:obj: object
=============================================

In a :term:`query expression` (generator expression) the
:data:`xotl.ql.core.this` objects stand for the entire universe of objects
*unless otherwise restricted by filter expressions*.  For instance::

    >>> from xotl.ql import this, thesefy

    >>> class Person(object):
    ...     pass

    >>> parents = (parent
    ...            for parent in this
    ...            if isinstance(parent, Person) and parent.children)

might be used to select every instance ``parent`` of ``Person`` that has a
non-null ``children`` children.


.. warning::

   It's up to the :term:`Query Translators <query translator>` to make any
   sense of this query.  Some translator may reject the query because it's not
   *computable* to the target storage system or just because it has some
   operation that is not supported.

   For instance if the target is a CouchDB_ database, the :func:`isinstance`
   operation might be rejected because CouchDB lacks types.  Alternatively, a
   query translator for CouchDB *might* have a configuration option to allow
   translation of this operation to a ``document._type == type``; where
   `_type` is the name of the attribute that is by convention used in CouchDB
   to store the objects' types.

   So when writing queries you should check the translators available and
   their documentation.


Queries are allowed to use `~xotl.ql.core.this`:obj: as much as they need to.
Nevertheless each apparition of ``this`` in a query is considered totally
independent of the others::

   pairs = ((boy, toy)
            for boy in this
	    for toy in this
	    if isinstance(boy, Person)
	    if boy.likes(toy))

In the previous query neither `boy` nor `toy` are automatically related by
being drawn from ``this``.  Instead the filters in the query establish the
relationship.  Furthermore, the query by itself does not restrict the type of
the `toy` variable, so it could potentially be bound to any type of object in
the data store.  It is up to both query writers and translator authors to
avoid this kind of situations.  Of course, translators *might* automatically
infer the type of `toy` given the hints provided in the query.


.. _order_limits_and_offsets:

Order, limits and offsets
=========================

So far, the query language presented does not allow for expressing neither
limits, offsets and order-by clauses.


Limits and offsets
------------------

To set limits and offsets you may pass the `partition` keyword argument a
`slice` object.  Every possible combination in python itself is possible here
as well.

.. _ref-translators-limit-expectations:

Compliant :term:`query translators` are required to:

- Raise a `TypeError` if they don't support `partition` and one is provided.

- Raise a `TypeError` if they don't support any of the `partition's`
  components that is not None (e.g. a translator may not support a step bigger
  than 1)

- Document those expectations.

The semantics associated with `partition` are the same as slices in Python.
Translators may restrict the domain for `start`, `stop` and `step` , however
they **must not** change the meaning of any of it's components.  Particularly,
the `stop` value in slices has *not* the same meaning that the clause `LIMIT`
in SQL (at least for PostgreSQL 9.1).  `LIMIT` refers to an *amount* of
elements to be returned, while `stop` refers to an *index*.

Translators may, for instance, restrict the use of negative indexes in
`partition` but **must not** regard `stop` as an amount instead of a index.


.. _ordering-expressions:

Expressing order instructions
-----------------------------

.. warning:: API in flux

   As with many of the API elements on xotl.ql, the API of the order is still
   in flux and may change as we improve on our work.  However, this part of
   the API is probably the one that will change the most due that is the less
   debated to the date.

To instruct a capable query translator to order the result you may pass the
`ordering` keyword argument.

The argument's type **must** be a callable (usually a lambda expression) that
receives as many positional arguments as selected elements are in the query
and returns either:

- A single *unary expression*, i.e. an expression tree of which its top most
  operator is one of :class:`xotl.ql.expressions.PositiveUnaryOperator` or
  :class:`xotl.ql.expressions.NegativeUnaryOperator`.

- A tuple of unary expressions of those.

Collectively those unary expressions are called "ordering expressions" in the
context of the interface :class:`xotl.ql.interface.IQueryObject`.

.. note::

   What you pass to the `ordering` argument of :class:`~xotl.ql.core.these`
   are not the ordering expressions themselves, but a procedure to build them
   from the selection.

Nothing more is enforced.

.. _ref-translators-ordering-expectations:

Compliant :term:`query translators <query translator>` are required to:

- Treat *positive* unary expressions as an *ascending* ordering request.

- Treat *negative* unary expressions as a *descending* ordering request.

- Further validate the expressions and raise a `TypeError` if any expression
  violates the type expectations of the translator.  This entails the
  requirement to clearly document those expectations.

This last requirement is need because the only type check that `xotl.ql` does
on `ordering` expressions is that they are *unary* ones, it is possible to
order by not only by *single term expressions*, but by more complex ones.

For instance a query may ask for ordering based on the result of the ratio
between the maximum value of an attribute in a sub-collection and other
attribute::

     query = these(
         (parent for parent in this),
         ordering=lambda parent: \
             +(max(child.age for child in parent.children)/parent.age)
     )

But some translators might be unable to correctly translate this kind of
ordering expression; maybe because the storage does not allow it or because
the translation process itself is not designed for such use cases.


.. _CouchDB: http://couchdb.apache.org/

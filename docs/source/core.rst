.. _query-lang:

========================================
The query language and the `this` object
========================================

The basic query language uses generator expressions to express both the SELECT
part and FILTER part of a query.

In a :term:`query expression` (generator expression) the :data:`this` objects
stand for the entire universe of objects *unless otherwise restricted by filter
expressions*. For instance::

    >>> from xotl.ql.expressions import count, is_a

    >>> class Person(object):
    ...     pass

    >>> parents = (parent for parent in this
    ...                   if is_a(parent, Person) & count(parent.children) > 0)

may be used to select every object ``parent`` that has an attribute
``children`` that is a non-empty sequence of objects.

The :data:`this` object may also appear in expressions meaning "the *current*
object"; when those expressions take a predicative form. For instance,
following the third interpretation for :class:`~xotl.ql.expression.all_`::

    >>> from xotl.ql.expressions import all_
    >>> parents = (parent for parent in this
    ...                if all_(parent.children, this.age > 10))

meaning to retrieve all `parents` whose children are all at least 10 years
(supposedly). In this case, the second use of the `this` object would represent
each child yielded by `parent.children`. But using the first interpretation for
`all_` would be more readable::

    >>> parents = (parent for parent in this
    ...                if all_(child.age > 10 for child in parent.children))


.. warning::

   It's up to the :term:`Query Translators <query translator>` to make any
   sense of this query. Some translator may reject the query because it's not
   *computable* to the target storage system or just because it has some
   operation that is not supported.

   For instance: if the target is a CouchDB_ database, the :class:`is_instance
   <xotl.ql.expressions.IsInstanceOperator>` operation might be rejected
   because CouchDB lacks types. Alternatively, a query translator for CouchDB
   *may* be configurable to translate this operation to a ``document._type ==
   type``; where `_type` is the name of the attribute that is by convention
   used in CouchDB to store the objects' types.

   So when writing queries you should check the translators available and their
   documentation.


:class:`!Term` instances may be *named*, thus allowing to select different
objects in a single query. When used in query expressions, `this` automatically
yields a single uniquely named :class:`Term` instance. So, you don't need to
specify a name by your self::

    >>> p, c = next((parent.name, child.name) for parent in this
    ...                        if count(parent.children) > 0
    ...                        for child in parent.children)

In order to have explicitly named instances you may provide a name::

    >>> parent, child = this('parent'), this('child')
    >>> q = ((p.name, c.name) for p in parent
    ...            if count(p.children) > 0 for c in child)

Providing a name may ease debugging tasks, and clarify log messages.

.. note::

   Notice that if you create an expression outside the context of a
   comprehesion you **must** provide names for instances that refer to
   different objects.  Otherwise the expression would not express what you
   intended. For instance::

     >>> from xotl.ql.expressions import in_
     >>> parent, child = this, this
     >>> expr = in_(child, parent.children)
     >>> expr2 = in_(child, this.children)

   Both ``expr`` and ``expr2`` are semantically equivalent::

     >>> with context(UNPROXIFING_CONTEXT):
     ...    expr == expr2
     True

   And you may see that the "natural" meaning of ``expr2`` entails "objects
   that are child of themselves", and that's probably not what we intended to
   express with ``expr``.

   Providing names avoids the confusion::

     >>> parent, child = this('parent'), this('child')
     >>> expr = in_(child, parent.children)
     >>> with context(UNPROXIFING_CONTEXT):
     ...    expr == expr2
     False


Order, limits and offsets
=========================

So far, the query language presented does not allow for expressing neither
limits, offsets and order-by clauses. But rest sure those things are
possible. When expressing a query :class:`~xotl.ql.core.these` allows to pass
many keyword arguments, which are kept in the :class:`query object
<xotl.ql.interfaces.IQueryObject>` returned.


Limits and offsets
------------------

To set limits and offsets you may pass the `partition` keyword argument a
`slice` object. Every possible combination in python itself is possible here as
well.

Alternatively, you may provide one (or several) of the keyword arguments:
`limit`, `offset` and `step`. This arguments are used then to create the
`slice` object. If you provide the `partition` argument, these ones will be
ignored (and a warning will be logged).

Compliant :term:`query translators` are required to:

- Raise a `TypeError` if they don't support `partition` and one is provided.

- Raise a `TypeError` if they don't support any of the `partition's` components
  that is not None (e.g. a translator may not support a step bigger than 1)

- Document those expectations.


.. _ordering-expressions:

Expressing order instructions
-----------------------------

To instruct a capable query translator to order the result you may pass the
`ordering` keyword argument to :class:`~xotl.ql.core.these`.

The argument's type **must** be a callable (usually a lambda expression) that
receives as many positional arguments as selected elements are in the query and
returns either:

- A single *unary expression*, i.e. an expression tree of which its top most
  operator is one of :class:`xotl.ql.expressions.PositiveUnaryOperator` or
  :class:`xotl.ql.expressions.NegativeUnaryOperator`.

- A tuple of unary expressions of those.

Collectively those unary expressions are called "ordering expressions" in the
context of the interface :class:`xotl.ql.interface.IQueryObject`.

.. note::

   What you pass to the `ordering` argument of :class:`~xotl.ql.core.these` are
   not the ordering expressions themselves, but a procedure to build them from
   the selection.

   What you get in the query's :attr:`xotl.ql.interfaces.IQueryObject.ordering`
   attribute are the ordering expressions as returned by the given procedure.

Nothing more is enforced.

Compliant :term:`query translators <query translator>` are required to:

- Treat *positive* unary expressions as an *ascending* ordering request.

- Treat *negative* unary expressions as a *descending* ordering request.

- Further validate the expressions and raise a `TypeError` if any expression
  violates the type expectations of the translator. This entails the
  requirement to clearly document those expectations.

This last requirement is need because the only type check that `xotl.ql` does
on `ordering` expressions is that they are *unary* ones, it is possible to
order by not only by *single term expressions*, but by more complex ones.

For instance a query may ask for ordering based on the result of the ratio
between the maximum value of an attribute in a sub-collection and other
attribute::

     from xotl.ql.expressions import max_
     query = these((parent for parent in this),
        ordering=lambda parent: +(max_(child.age for child in parent.children)/parent.age))

But some translators might be unable to correctly translate this kind of
ordering expression; maybe because the storage does not allow it or because the
translation process itself is not designed for such use cases.


.. _CouchDB: http://couchdb.apache.org/

.. _query-lang:

========================================
The query language and the `this` object
========================================

.. module:: xotl.ql.core

Extends the :mod:`~xotl.ql.expressions` language to provide universal
accessors.

The :obj:`this` object stands for every object in the "universe" (e.g. the
index, the storage, etc.) :obj:`this` eases the construction of expressions
directly, and also provides a query language by means of Python's syntax for
:ref:`generator expressions <py:generator-expressions>` and list, and dict
comprehensions (we shall call them comprehensions).


An overview of the Query Language
=================================

The basic query language uses comprehensions to express both the SELECT part
and FILTER part of a query.

In a query (comprehension) the :data:`this` objects stand for the entire
universe of objects *unless otherwise restricted by filter expressions*. For
instance::

    >>> from xotl.ql.expressions import count
    >>> parents = (parent for parent in this if count(parent.children) > 0)

may be used to select every object ``parent`` that has an attribute
``children`` that is a non-empty sequence of objects.

The :data:`this` object may also appear in expressions meaning "the *current*
object"; when those expressions take a predicative form. For instance, with
the third form of :class:`~xotl.ql.expression.all_`::

    >>> from xotl.ql.expressions import all_
    >>> parents = (parent for parent in this
    ...                if all_(parent.children, this.age > 10))

meaning to retrieve all `parents` whose children are all at least 10 years
(suppodsely). Of course, using the first form for `all_`, would be more
readable::

    >>> parents = (parent for parent in this
    ...                if all_(child.age > 10 for child in parent.children))


.. warning:: It's up to the :term:`Query Translators <query translator>` to
             make any sense of this query. Some translator may reject the query
             because it's not *computable* to the target storage system or just
             because it has some operation that is not supported. 

	     For instance: if the target is a CouchDB_ database, the
	     :class:`is_instance <xotl.ql.expressions.IsInstanceOperator>`
	     operation might be rejected because CouchDB lacks types. Of
	     course, a query translator for CouchDB *should* be configurable to
	     translate this operation to a ``document._type == type``; where
	     `_type` is the name of the attribute that is by convention used in
	     CouchDB to store the objects' types.

             So when writing queries you should check the translators available
             to you and their documentation.


:class:`!These` instances may be *named*, thus allowing to select different
objects in a single query. When used in comprehensions, `this` automatically
yields a single uniquely named :class:`These` instance. So, you don't need to
specify a name by your self::

    >>> p, c = next((parent.name, child.name) for parent in this
    ...                        if count(parent.children) > 0
    ...                        for child in parent.children)

In order to have explicitly named instances you may provide a name::

    >>> parent, child = this('parent'), this('child')
    >>> q = ((p.name, c.name) for p in parent
    ...            if count(p.children) > 0 for c in child)

Providing a name may ease debugging tasks, and clarify log messages.

Notice that if you create an expression outside the context of a comprehesion
you **must** provide names for instances that refer to different objects.
Otherwise the expression would not express what you intended. For instance::

    >>> from xotl.ql.expressions import in_
    >>> parent, child = this, this
    >>> expr = in_(child, parent.children)
    >>> expr2 = in_(child, this.children)

Both ``expr`` and ``expr2`` are semantically equivalent::

    >>> with context(UNPROXIFING_CONTEXT):
    ...    expr == expr2
    True

And you may see that the "natural" meaning of ``expr2`` entails "objects that
are child of themselves", and that's probably not what we intended to express
with ``expr``.

Providing names avoids the confusion::

    >>> parent, child = this('parent'), this('child')
    >>> expr = in_(child, parent.children)
    >>> with context(UNPROXIFING_CONTEXT):
    ...    expr == expr2
    False


External API for the query language
===================================

In this section we give the details of the (external) query API. For the
internal query API, used to those that need to build extensions of the query
language, please refer to :ref:`query-api`.

As we've said, at the core of the Query Language is the `this` object, whose
type is a subclass of the `These`. The following describe both objects:

.. autodata:: this

.. autoclass:: These
   :members:



.. _CouchDB: http://couchdb.apache.org/

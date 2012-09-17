.. _glossary:

==================
Terms and glossary
==================

.. glossary::

   expression tree

       The tree that represents an expression as it was syntactically
       constructed.  Usually the inner nodes of the tree represents the
       operations and the leaves the "atomic" operands.

       For instance, the expression tree for the expression ``2**4 + 3`` would
       have as its root node the `+` symbol, the children of which would be:

         a) the expression tree for ``2**4``, that would have `**` as its root
            node, and literals `2` and `4` would be its children.

         b) the literal `3`

       In the expression language as implemented in :mod:`xotl.ql.expressions`,
       operations are always classes derived from
       :class:`~xotl.ql.expressions.Operator`, and the operands are any python
       object (sometimes you need to enclose such an operand inside a
       :class:`~xotl.ql.expressions.q` object). The class
       :class:`~xotl.ql.expressions.ExpressionTree` represents such a tree.


   function object operator
   functor operation
   functor operator

       Represents the kind of :term:`operations <operation>` that are
       normally expressed by the invocation of a function, i.e: the
       `abs`, `max` and `min` functions. This kind of operation is in
       contrast with those that are syntactically expressed with
       symbols like the addition operation usually encoded with the
       `+` symbol.

       This is just a syntactical distinction, and not a fundamental
       one. It's perfectly possible to build the expression that
       express the addition of `1` and `2` like this:

       .. doctest::

	  >>> from xotl.ql.expressions import add
	  >>> add(1, 2)                 # doctest: +ELLIPSIS
	  <expression '1 + 2' ...>

       However it's more natural to encode such expressions with the
       usual plus sign, like this:

       .. doctest::

          >>> from xotl.ql.expressions import q
          >>> q(1) + 2              # doctest: +ELLIPSIS
          <expression '1 + 2' ...>

   OMCaF
   Objects Model Canonical Form

       An ongoing effort to build a model for object-oriented systems with
       semantics included. Part of the (yet unreleased) `xotl.model` package.

   query

       The term `query` is used in this documentation with two
       meanings that depend on the context:

       a) The comprehension as seen in the code that express what is
	  intended to fetch from the storage(s).

       b) The (internal) data structure that represents the query (as
          in item a) to the program.

       Most of the time we talk about type-a queries, but in the internal API
       documentation it's necessary to distinguish between the type-a query and
       it's structure.

   query translator
   translator

       In the general design a query translator is a component that
       receives a :term:`query` and produces a :term:`query execution
       plan`. The query is usually the result of the
       :func:`~xotl.ql.core.these` function; and the execution plan
       is dependant of the translator. A CouchDB translator, for
       instance may simply translate the whole query to a CouchDB view
       and return a plan that just involves quering that view.

       Query translator are not implemented on this package.


   query execution plan

       When a :term:`query` is processed by a :term:`query translator` it
       produces an execution plan. Such a plan is a sort of *compiled form* of
       the query.

       The execution plan should include instructions to retrieve the objects
       expected. An execution plan may be as simple as:

           just execute the SQL query ``SELECT * FROM sometable [WHERE ... ]
	   [ORDER BY ...] [OFFSET ...]`` against the default relational
	   database;

	   then, return an iterator for instances of those objects created by
	   the factory class ``ISomeModel``.

       to another plan that checks an SQL index and the fetches objects from a
       REST interface.

       The execution plan in this package is not subject to any design
       restrictions, is just noted that it may be a good
       implementation path to follow to transform a `xotl.ql` query
       into another object (the plan) that may be better suited to be
       executed against your storage(s) media.

.. _glossary:

==================
Terms and glossary
==================

.. glossary::

   data set

     An object that represents the result of executing a :term:`query` against
     a define :term:`storage`. It should implement the interface
     :class:`xotl.ql.interfaces.IDataSet`, which is quite flexible since it
     only requires the data set to be iterable using the `next` protocol.

   execution context

      An object that represents the context in which a given piece of code is
      being executed. Contexts may influence how objects behaves. Every process
      and thread entail an execution context, and they may form a tree.

      Currently a very simple implementation of execution contexts is in the
      module :ref:`xoutil.context`.

      A future more comprehensive implementation is planned to be in
      :ref:`xotl.context`; where contexts are though to be queriable using
      `xotl.ql` query language.

   expression tree

       The tree that represents an expression as it was syntactically
       constructed.  Usually the inner nodes of the tree represents the
       operations and the leaves the "atomic" operands.

       For instance, the expression tree for the expression ``3 + 4**2 <
       18983`` would have as its root node the `<` symbol, the children of
       which would be:

         a) the expression tree for ``3 + 4**2``, that would have `+` as its root
            node, and the literal `3` and the expression tree for ``4**2`` as
	    its children.

         b) The literal `18983`.

       This tree is depicted in the following image:

       .. image:: figs/expr-tree.png

       In the expression language as implemented in :mod:`xotl.ql.expressions`,
       operations are always classes derived from
       :class:`~xotl.ql.expressions.Operator`, and the operands are any python
       object. The class :class:`~xotl.ql.expressions.ExpressionTree`
       represents such a tree.


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

   generator token

       A generator token is an expression that is used inside a :term:`query`
       as a named location from which to draw objects. It relates to the FROM
       clause in SQL, and to the ``<-`` operation in UnQL [UnQL]_.

       In the query::

	 these((parent, child) for parent in this if parent.age > 34
	                       for child in parent.children if child.age < 2)

       There are two such tokens: the first captures the iteration over
       ``this`` and the second, the iteration over ``parent.children``.

       See :class:`xotl.ql.interfaces.IGeneratorToken` for details.

   object model

       An object model is an object-oriented model which describes how objects
       may exist and how they may relate to each other.

       This include relational model; in such a model an object is a single
       collection of named scalars that belongs to a single entity. Relations
       are just foreign-keys, and the semantics associated with relations is
       that of referential integrity.

       A relational database is a kind of :term:`storage` that uses the
       relational model as is object model (usually with some variations).

       `xotl.ql` does not provides an API for expressing object models, but it
       assumes that a :term:`translator <query translator>` exists which has
       enough knowledge to deal which such an object model.

       .. todo::

	  Wouldn't the semantics of a object model be capture by category
	  theory?

	  The authors of [coSQL2011]_ point that this is possible; but I've not
	  study that much yet ;)


   OMCaF
   Objects Model Canonical Form

       An ongoing effort to build a model for object-oriented systems with
       semantics included. Part of the (yet unreleased) `xotl.model` package.

   query

       The term `query` is used in this documentation with two meanings that
       depend on the context:

       a) The comprehension as seen in the code that express what is
	  intended to fetch from the storage(s).

	  In the most part of this documentation the term `query` will refer to
	  this sense of the word. However, to disambiguate we'll use the term
	  :term:`query expression` to refer to this sense of the word if
	  needed.


       b) The (internal) data structure that represents the query (as
          in item a) to the program.

	  We prefer the term :term:`query object` for this sense of the word,
	  but sometimes it just does not matter.

   query expression

      This term is used solely to distinguish a :term:`query` as the
      construction expressed in the (Python) language from the internal data
      structure (:term:`query object`).

   query object

      This term is used solely to distinguish a :term:`query` as an internal
      data structure in contrast to the language construction (i.e the first
      meaning for the term :term:`query`) that implies such a structure.

   query translator
   translator

       In the general design a query translator is a component that receives a
       :term:`query object` and produces a :term:`query execution plan`. The
       query execution plan depends on the translator for it encompasses the
       knowledge about both the :term:`object model` and the :term:`object
       storage <storage>`. A CouchDB translator, for instance may simply
       translate the whole query to a CouchDB view and return a plan that just
       involves quering that view.

       There no (serious) translators implemented on this package.

   query execution plan

       When a :term:`query object` is processed by a :term:`query translator`
       it produces an execution plan. Such a plan is a sort of a *compiled
       form* of the query.

       The execution plan should include instructions to retrieve the objects
       expected. An execution plan may be as simple as:

           just execute the SQL query ``SELECT * FROM sometable [WHERE ... ]
	   [ORDER BY ...] [OFFSET ...]`` against the default relational
	   database;

	   then, return an iterator for instances of those objects created by
	   the factory class ``ISomeModel``.

       to another plan that checks an index stored in a SQL database, but
       fetches objects from a remote system through REST interface.

       The :class:`interface for a query execution plan
       <xotl.ql.interfaces.IQueryExecutionPlan>` in this package places almost
       no restrictions, it just requires that the execution is a callable that
       returns an iterable :term:`data set` using the `next` protocol.

   storage
   object storage

       A software component that allows to "persists" objects. Most of the time
       the storage relates to a single :term:`object model`. For instance
       relational databases use the relational model.

       In general, a storage is a place from which one could draw objects
       from. We may then, relax the "persistence" requirement from a component
       to be considered a storage. For instance, a `memcached` server may be
       considered a key-value storage, that a query translator may target.

   thread-local object

       A thread-local object is an instance of the ``threading.local``
       class. An instance of this class acts like a global variable, but it
       holds values local to a given thread; so, each thread has its own
       "global" variable. Please refer to Python's documentation for more
       information.

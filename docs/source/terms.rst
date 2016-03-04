.. _glossary:

==================
Terms and glossary
==================

.. glossary::
   :sorted:

   AST
   Abstract Syntax Tree

      A tree structure that represents a *program* in source form as a tree of
      syntactical elements; but removes several too concrete elements of the
      syntax; for instance in AST sentences separator are often removed and a
      subtree for each individual sentence appears.

      See more on http://en.wikipedia.org/Abstract_Syntax_Tree

   byte-code

      Refers to the low-level code into which the Python interpreter compiles
      the source code.

      For instance, given the query expression (generator object)::

        >>> from xotl.ql.core import this
        >>> query = (parent for parent in this)

      The byte code of the generator object is (in Python 2.7)::

	|\x00\x00]\x0b\x00}\x01\x00|\x01\x00V\x01q\x03\x00d\x00\x00S

      Often the byte-code is shown in an expanded form that eases the task of
      reading it.  The module `dis`:mod: prints this expanded form::

	>>> import dis
	>>> dis.dis(query.gi_code)                          # doctest: +SKIP
	2           0 LOAD_FAST                0 (.0)
	      >>    3 FOR_ITER                11 (to 17)
		    6 STORE_FAST               1 (parent)
		    9 LOAD_FAST                1 (parent)
		   12 YIELD_VALUE
		   13 POP_TOP
		   14 JUMP_ABSOLUTE            3
	      >>   17 LOAD_CONST               0 (None)
		   20 RETURN_VALUE

   data set

      An object that represents the result of executing a :term:`query`
      against a defined :term:`storage`.  It should implement the interface
      :class:`xotl.ql.interfaces.IDataSet`, which is quite flexible since it
      only requires the data set to be iterable using the `next` protocol.

   object model

      An object model is an object-oriented model which describes how objects
      may be and how they may relate to each other.

      This include relational model; in such a model an object is a single
      collection of named scalars that belongs to a single entity.  Relations
      are just foreign-keys, and the semantics associated with relations is
      that of referential integrity.

      A relational database is a kind of :term:`storage` that uses the
      relational model as is object model (usually with some variations).

      `xotl.ql` does not provides an API for expressing object models, but it
      assumes that a :term:`translator` exists which has enough knowledge to
      deal which such an object model.

      .. todo::

         Wouldn't the semantics of an object model be captured by category
         theory?

         The authors of [coSQL2011]_ point that this is possible; but I've not
         study that much yet ;)


   query

      The term `query` is used in this documentation with two meanings that
      depend on the context:

      a) The generator expression as seen in the code that express what is
         intended to fetch from the storage(s).

         In the most part of this documentation the term `query` will refer to
         this sense of the word.  However, to disambiguate we'll use the term
         :term:`query expression` to refer to this sense of the word if
         needed.


      b) The (internal) data structure that represents the query (as in
         item a) to the program.

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

      In the API documentation this means any object that complies with the
      interface `xotl.ql.interfaces.QueryObject`:class:.

   query translator
   translator

      In the general design a query translator is a component that receives a
      :term:`query object` and produces a :term:`query execution plan`.  The
      query execution plan depends on the translator for it encompasses the
      knowledge about both the :term:`object model` and the :term:`object
      storage <storage>`.  A CouchDB translator, for instance may simply
      translate the whole query to a CouchDB view and return a plan that just
      involves quering that view.

      In the API documentation this means any object that complies with the
      interface `xotl.ql.interfaces.QueryTranslator`:class:.

   transformation

      Is the process of modifying a `query object`:term: into another one.

   query execution plan

      When a :term:`query object` is processed by a :term:`query translator`
      it produces an execution plan.  Such a plan is a sort of a *compiled
      form* of the query.

      The execution plan should include instructions to retrieve the objects
      expected.  An execution plan may be as simple as:

        just execute the SQL query ``SELECT * FROM sometable [WHERE ... ]
        [ORDER BY ...] [OFFSET ...]`` against the default relational database;

        then, return an iterator for instances of those objects created by the
        factory class ``SomeModel``.

      Or it can be one that checks an index stored in a SQL database, but
      fetches objects from a remote system through REST interface.

      In the API documentation this means any object that complies with the
      interface `xotl.ql.interfaces.QueryExecutionPlan`:class:.


   QST
   Query Syntax Tree

      A type of `abstract syntax tree`:term:.  It describes the syntactical
      structure of a `query expression`:term:.

      Since the introduction of the `revenge module <xotl.ql.revenge>`:mod:
      that uses compiler techniques to reverse engineer the Python
      `byte-code`:term:, the term AST was being used both as inner structure
      and as the main structure used by `query translators <query
      translator>`:term:.  To disambiguate, the QST term specifically
      describes the AST that `xotl.ql` produces as its output; whereas AST is
      a more generic term that covers all AST structures, but most of the time
      will refer to *intermediate* structures.

   reverse engineering

      Refers to either the (intellectual) activities, processes, and
      techniques to obtain the original Python source code given a
      `byte-code`:term: string.

      Depending on the compiler this is not always possible or it may result
      in a code that is not 100% identical to the original but that would
      produce the same byte-code as the original.  For instance the following
      two query expressions produce the same byte-code::

         >>> g1 = (parent
         ...      for parent in this
         ...      if parent.age > 1
         ...      if parent.children)

         >>> g2 = (parent
         ...      for parent in this
         ...      if parent.age > 1 and parent.children)

	 >>> g1.gi_code.co_code  == g2.gi_code.co_code
	 True


   storage
   object storage

      A software component that allows to "persists" objects.  Most of the
      time the storage relates to a single :term:`object model`.  For instance
      relational databases use the relational model.

      In general, a storage is a place from which one could draw objects from.
      We may then, relax the "persistence" requirement from a component to be
      considered a storage.  For instance, a `memcached` server could be
      considered a key-value storage, that a query translator might target.

   thread-local object

      A thread-local object is an instance of the ``threading.local`` class.
      An instance of this class acts like a global variable, but it holds
      values local to a given thread; so, each thread has its own "global"
      variable.  Please refer to Python's documentation for more information.

..
   Local Variables:
   indent-tabs-mode: nil
   End:

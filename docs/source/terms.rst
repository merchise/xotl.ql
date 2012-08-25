.. _glossary:

==================
Terms and glossary
==================

.. glossary::

   query
       The term `query` is used in this documentation with two
       meanings that depend on the context:

       a) The comprehension as seen in the code that express what is
	  intended to fetch from the storage(s).

       b) The (internal) data structure that represents the query (as
	  in item a) to the program.


   query translator
   translator
       In the general design a query translator is a component that
       receives a :term:`query` and produces a :term:`query execution
       plan`. The query is usually the result of the
       :func:`~xotl.ql.these.these` function; and the execution plan
       is dependant of the translator. A CouchDB translator, for
       instance may simply translate the whole query to a CouchDB view
       and return a plan that just involves quering that view.

       Query translator are not implemented on this package.

   query execution plan 
       When a :term:`query` is processed (by a :term:`query
       translator`) it produces an execution plan. The execution plan
       should relate how to retrieve the objects expected; an
       execution plan may be as simple as "just execute the SQL query
       ``SELECT * FROM objects ...`` against the default relational
       database", to another plan that checks an SQL index and the
       fetches objects from a REST interface.

       The execution plan in this package is not subject to any design
       restrictions, is just noted that it may be a good
       implementation path to follow to transform a `xotl.ql` query
       into another object (the plan) that may be better suited to be
       executed against your storage(s) media.

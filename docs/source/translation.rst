.. _translation:

=========================
Translating query objects
=========================

Translation is the process that transforms a :term:`query object` into a form
feasible for execution in a :term:`data store <storage>` and/or :term:`object
model`.  The result of translating a query is a :term:`query execution plan`.

:term:`Query translators <query translator>` are the components responsible
for translation.  `xotl.ql` does not provide production quality translators,
but other packages are planned to have implementation of translators.
Nevertheless, the module :mod:`xotl.ql.translation.py` provides an
implementation of *naive* translator that matches the Python object model and
fetches objects from the current process memory.

.. note:: This section is mostly relevant for translation authors only.

   It contains details that are not important for application writers.
   However, application writers might profit from these notes in order to
   better understand possible exceptions they are facing.


General requirements about translators
======================================

Take query expressions and query objects
----------------------------------------

Translators are required to take either a `query expression`:term: or a `query
object`:term:.  For this, translators could use
`xotl.ql.core.normalize_query`:func:.


Re-usability of execution plans
-------------------------------

Translators must allow the reuse of execution plans; i.e. once a query is
translated you may execute the plan several times to fetch the objects that
matches the query at the time the plan is executed.

This way one may use the translator only once per query and then reuse plan
for several calls to retrieve objects.

This does not mean that each time you execute the plan it will return the same
objects since the underlying data storage system might have been changed
between calls.

This does not imply that plans should be cached either.  If the translation
process is executed many times for the same query, translators may return
different (although equivalent) plans each time.


Documentation requirements
--------------------------

Translators authors are encouraged to provide as much documentation as
necessary, so that application writers have the guidance they need for writing
queries.

.. warning:: Documentation in flux.


We feel the following information is *required* in order for a translator
documentation be complete:

- A list of the supported expression operations.  For instance, a translator
  might reject operations involving `max`:func: or `min`:func: or allow them
  only in some cases.

- A list of additionally supported operations, and their related
  documentation.  Package that implements translators may provide
  non-standards functions (e.g, a `coalesce` function available for SQL
  translators).

- Documentation of functions, classes applications writers may use to access
  the translator functionality directly if they have to.

======================================================================
:mod:`xotl.ql.translation.py` -- A test bed translator for Python's VM
======================================================================

.. module:: xotl.ql.translation.py


This modules implements a naive translation algorithm from :term:`query objects
<query object>` to a simple execution plan that fetches objects residing in
Python's memory that matches the query.

.. warning:: This module is not intended for production use. It is just a
	     sketch of how a translator might be constructed. However modestly,
	     it also serves the purpose of showing off the query language in
	     action.

.. function:: naive_translation(query, **kwargs)

   Takes a :term:`query object` and returns an :term:`query execution
   plan`.

   Once the plan is returned it may be called several to get, each time, the
   matching objects. This is, you don't have to do the translation process each
   time you need to fetch objects.

   This function *does not* keep a cache from :term:`query objects` to
   execution plans.

   Currently no ordering or partitioning is performed.

   Besides normal arguments, you may also pass:

   :param only: A sequence of package/module names from which you'd like to
		drawn objects from.

		Since the returned plan uses ``gc.get_objects()`` to get the
		current objects in Python's memory, this allows to reduce the
		amount of objects passed to the query filters, and improves the
		performance a bit.

   Usage::

         query = these(child for parent in Person
                       if parent.childs & (parent.age > 30)
                       for child in parent.childs
                       if child.age < 10)
	 plan = naive_translation(query)

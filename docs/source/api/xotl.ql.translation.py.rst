======================================================================
:mod:`xotl.ql.translation.py` -- A test bed translator for Python's VM
======================================================================

.. module:: xotl.ql.translation.py


This modules implements a "naive translation" algorithm from :term:`query
objects <query object>` to a simple execution plan that fetches objects
residing in Python's memory.

.. warning:: This module is not intended for production use. It is just a
	     sketch of how a translator might be constructed. However modestly,
	     it also serves the purpose of showing off the query language in
	     action.

Functions
=========

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


.. autofunction:: init(settings=None)


Details of this translator
==========================

This module is not intended to be extensible. It expressions that involve only
the functions from :mod:`xotl.ql.expressions`. Any other custom function will
not be translated and an error will be issued at translation.


.. instances-class-protocol:

Searching a custom object base
------------------------------

When the execution plan returned by this translation needs to find an object,
it normally iterates throughout the objects in the Python memory by using
``gc.get_objects()``. This may be expensive [#pypy] cause Python might have
lots of objects in memory while only a few of them are of interest.

To alleviate this situation, this translation offers the following protocol: If
it can statically determine the class of a given top-level generator token and
that class has an attribute `this_instances` that is a collection (i.e a list,
tuple, generator object, but not a dict nor a string); then only the items in
the `this_instances` collection are used to replace the token's apparitions in
the query.

For instance::

      @thesefy
      class Universe(int):
         pass
      Universe.this_instances = [Universe(i) for i in range(2, 10)] + ['invalid']

      query = these(atom for atom in Universe)

The previous query have a single filter ``is_instance(atom, Universe)`` --
which is automatically injected by :func:`~xotl.ql.core.thesefy`. And since
Universe does a `this_instances` attribute that holds a list of objects, those
will be the only ones inspected by this translator.

Notice that despite `this_instances` contains a string element, this element
won't pass the `is_instance` check, so it won't be returned by the execution
plan.



The guts
========

.. autoclass:: var

.. autoclass:: vminstr


Footnotes
=========

.. [#pypy]

   For instance, PyPy creates lots of objects at the very start::

     $ pypy -c "import gc; print(len(gc.get_objects()))"
     21437

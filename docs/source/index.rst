.. xotl.ql documentation master file, created by
   sphinx-quickstart on Fri Jun 29 12:53:45 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

``xotl.ql`` |release| documentation
===================================

This package provides *facilities* to implement query languages in python.
The query language is based on Python's generator expression.  A query in this
language looks like this::

    >>> from xotl.ql.core import parse_query, this

    >>> query = parse_query(
    ...    child
    ...    for parent in this
    ...    if parent.children and parent.age > 32
    ...    for child in parent.children
    ...    if child.age < 6
    ... )

The result of the :class:`~xotl.ql.core.parse_query` callable is a
:term:`query object` that "describes" at the syntactical level the
:term:`query expression` above.


What's new in this release?
---------------------------

.. include:: history/changes-0.3.0.rst



Core Contents:
--------------

.. toctree::
   :glob:
   :maxdepth: 1

   overview
   translation
   api/*
   terms
   HISTORY
   credits
   license

Additional documents:
---------------------

.. toctree::
   :maxdepth: 1

   ponyorm
   thoughts
   _revenge/index
   monads
   scratch
   references
   changes/index

What does xotl mean?
--------------------

The word "xotl" is a Nahuatl word that means foundation, base.  The `xotl`
package comprises the foundation for building reliable systems, frameworks,
and libraries.  It also provides an object model that allows to build complex
systems.

It is expected that `xotl` will use `xotl.ql` to:

- Express predicates defining object relationships
- Query the object store (of course!)
- Update the object store.

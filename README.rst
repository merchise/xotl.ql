The *pythonic* query language
=============================

This package provides a library for implementing query languages for Python.
The syntax is based on Python's generator expression.  A query in this
language looks like this::

    >>> from xotl.ql.core import this, get_query_object

    >>> query = get_query_object(
    ...    child
    ...    for parent in this
    ...    if parent.children and parent.age > 32
    ...    for child in parent.children
    ...    if child.age < 6
    ... )

The resultant `query` is an object that "describes" at the syntactical level
the query expression above.

Full documentation kept at `Read the doc <http://xotl-ql.readthedocs.org/>`_.


How to contribute
-----------------

You may contribute as much as you like, and by any means you feel the project
may be helped.  If is code what you may apport; just fork this project make
changes and place a pull request.


What does xotl mean?
--------------------

The word "xotl" is a Nahuatl word that means foundation, base.  The `xotl`
package comprises the foundation for building reliable systems: both
frameworks, libraries and an object model that allows to build complex
systems.

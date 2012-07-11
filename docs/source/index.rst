.. xotl.ql documentation master file, created by
   sphinx-quickstart on Fri Jun 29 12:53:45 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to xotl.ql's documentation!
===================================

.. automodule:: xotl.ql

.. warning::

   We're still working to improve this language. In particular we're
   trying to simplify it's current implementation by using more
   granular types instead of context of executions.

   We believe however, that "esence" is already achieve. Here are some
   TODOs:

   1. Eliminate the :class:`~xotl.ql.these.AUTOBINDING_CONTEXT` by
      yielding a different type in the `__iter__` method, and possibly
      implement the `next` protocol ourselves.

   2. It's been suggested to change the name of
      :func:`~xotl.ql.these.query` to `these`.

   3. Allow operation-less conditions like::

	valid = (who for who in this if who.valid)


Contents:

.. toctree::
   :maxdepth: 2

   expressions
   these
   translate
   references
   HISTORY
   credits
   license



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


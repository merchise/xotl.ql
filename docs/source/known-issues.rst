==============
 Known issues
==============

.. _known-issues-0.3.0:

At release 0.3.0
================

- Pypy support is not complete.  Expressions like ``(x for x in this if not
  p(x) or z(x) or not h(x))`` fail to be recognized.

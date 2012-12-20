=============================================================
A common query translation framework and translation test bed
=============================================================

.. module:: xotl.ql.translate

Translation
===========

Translation is the process by which a :term:`query object` is translated to a
:term:`query execution plan` given (or assumed) an :term:`object model` and/or
:term:`storage`.


Utilities provided by :mod:`xotl.ql.translate` module
=====================================================

.. autofunction:: cofind_tokens(expr, accept=None)

.. autofunction:: cocreate_plan(query, **kwargs)


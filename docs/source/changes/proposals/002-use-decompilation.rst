==========================================
 Use Python byte-code reverse engineering
==========================================

This proposal removes the entire API in favor of byte-code reverse
engineering.


:XEP: 002 -- Use Python byte-code reverse engineering
:Status: Approved, In progress.
:Author: Manuel Vázquez Acosta
:Branch: develop


Rationale
=========

Trying to guess the AST of a query has proven cumbersome and in requirement of
several hacks like the "particles bubble" to capture events that passed long
before.

Furthermore, the queries needed to be specially crafted for the query
language, i.e we could not use the ``and``, ``or``, ``in``, ``is`` and other
keywords in the queries.  The same happened for built-in functions like
`all`:func:, `any`:func:, `sum`:func:, `max`:func: and `min`:func.  There were
all being replicated in the expression language.

Since then the `uncompyle2` package showed an Early Grammar that's fairly easy
to modify to build a recognizer for Python's byte-code and extract an AST.
Previous experimentation proved it would be practical to adapt it to the query
language needs.

Besides, the article [MCQL]_ provides a language for queries.  This language
could be used to bootstrap an AST for queries in Python, taking into account
several facts proven in the article that don't apply to Python.


Inclusion rationale
===================

Changes in the API
------------------

This is a total rewrite of the module, so the API is heavily changed.  The
following remarks are not the only things that changed but some highlights
about the changes:

- We are not using ``zope.component`` anymore.  Those are deemed outside the
  scope of an AST for Query Languages.

- The object ``this`` is becoming more nominal, since it won't play major
  role.  Most of the time, it would only be used to bootstrap comprehensions.

- The expression language is Python, so the module :mod:`xotl.ql.expressions`
  will be rethought into utilities for expressions or will be totally removed.


Non-inclusion rationale
=======================

Not given.

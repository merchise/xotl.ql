.. _pony:
=====================
Comparison with Pony_
=====================

:Date: Tue Apr 30, 2013 (2013-04-30.)
:Last Updated: Mon Nov 9, 2015 (2015-11-09)
:Document status: Final.
:Author: Manuel Vázquez Acosta (`@mvaled`__)
:Summary: Describes and compares PonyORM and xotl.ql.  Proposes to explore
          bytecode disassembling as way to implement `xotl.ql`.

__ http://twitter.com/mvaled/

Pony_ is an ORM_ implementation that shares our vision of writing queries
using the generator expressions of Python.  Their queries look like::

   persons = select(p for p in Person if 'o' in p.name)

The project seems to be started in 2006, but I have just discovered today.
And I like some of the external features it exposes; like the use of the true
logical ``and`` and ``or`` binary operators; and everything we have had to
circumvent in `xotl.ql` so far.

In this document I would like to describe how Pony_ is different/similar to
`xotl.ql` and how they might influence our future work.


.. note:: Update 2015-11-07.

   I updated my Pony clone today, and realized they're now targeting both
   Python 2 and Python 3.  So they're still an interesting project to learn
   from.


What Pony is that `xotl.ql` is not
==================================

Pony is an ORM
--------------

Pony is an ORM_; meaning it concerns itself with interacting with a
*relational database* like SQLite, MySQL and PostgreSQL.

`xotl.ql` does not aim to target any specific :term:`object model` not even
the relational model, and thus it does not aim to target any specific database
system.  This job is left to :term:`query translators <query translator>` to
perform.

In this regard `xotl.ql` does what the :ref:`pony.decompiling <decompiling>`
module does; only different.

This is the only true difference in the broader aim that Pony and xotl.ql
have.  However, they differ a lot in design and implementation.

.. _decompiling:

Pony disassembles the Python bytecode
-------------------------------------

Python does not make it easy to hook the logical operators ``and``, ``or`` and
``not``.  There are no protocols for them.  Additionally, the protocols for
working with the ``in`` containment test operator always change the result to
a boolean.  These rules make it impossible to create a complete expression
language using *normal* Python code.

Pony overcomes this difficulty by inspecting the low-level bytecode the Python
interpreter generates for the generator object.  This is way they can
reconstruct an :term:`AST` that is *semantically equivalent*
[#syntactical-eq]_ to the original expression.

The `xotl.ql` way is fully explained in :ref:`inner-workings`.  Basically we
tried to keep our implementation abstracted from Python's implementation
details like the bytecode.  Full disclosure: although we knew the existence of
the bytecode, we did not knew "the CPython bytecode".  Furthermore, we thought
it wasn't needed and probably should be avoided to gain interoperability
between Python's implementations (``xotl.ql`` works the same over Python 2.7
than over Python 3.2).

Perhaps we were wrong.  Perhaps what we should have done is study the several
bytecodes for our target Python implementations and have implementations for
those.  Which leads me to:


How does Pony might influence our future work?
==============================================

Perhaps the most impacting feature we would love to have is to write our
queries with *true* Python operators and not having ``&`` for ``and``; and
:mod:`~xotl.ql.expressions.all_` for ``all()`` and the like.

This would transform the usage of our expression language for queries; though,
the expression languages for predicates would probably suffer.  Nevertheless we
would still need :class:`~xotl.ql.core.these`, so we might just require
predicates to be lambdas (which would be cool actually).

But we would keep our main goal of not being a data-accessing layer.  So what
would change and what wouldn't change if we pursue this avenue:

- We would keep the concept of a :term:`query
  translator`.  :class:`~xotl.ql.core.these` will always return a (probably
  changed) :class:`xotl.ql.interfaces.IQueryObject` with the AST of the query.

- Syntactical pairing of :term:`query expressions <query expression>` and
  :term:`query objects <query object>` would be lost.  However, semantics would
  be kept.

- Whether or not the Python ``ast`` module is a fit for our query/expression
  language is still not clear.  See :ref:`lit-review`, specially the
  [coSQL2011]_ reference.  Probably the Python's AST serves as an internal
  intermediary language, but the AST exposed to translators would probably
  resemble the monadic query language.  At this moment I just don't know.

Next steps
----------

In the next weeks I'll be doing the following:

#. Study the Python 2.7 bytecode as explained in :mod:`dis` standard module and
   other Internet public sources.

   I can use the ``pony.decompiling`` as a starting point.  See `the tweets`__.

#. Do the same for Python 3.2 and probably Python 3.3.

#. Propose a new API in an experimental branch.

__ https://twitter.com/mvaled/status/330045481671602176

Footnotes
=========

.. [#syntactical-eq]

   Syntactical equivalence might not possible this way since Python uses the
   same bytecode for different syntactical constructions.

   For example the following generators, which are *semantically equivalent*
   (but not syntactically) generate the same bytecode::

      this = iter([])
      g1 = (parent
            for parent in this
            if parent.age > 1
            if parent.children)

      g2 = (parent
            for parent in this
            if parent.age > 1 and parent.children)


.. _Pony: http://ponyorm.com/
.. _ORM: http://en.wikipedia.org/wiki/Object-relational_mapping

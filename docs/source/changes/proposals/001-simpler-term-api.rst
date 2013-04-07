===================================================
Simpler :class:`xotl.ql.interfaces.ITerm` interface
===================================================

This proposes to simplify the :class:`xotl.ql.interfaces.ITerm` to remove the
:attr:`~!xotl.ql.interfaces.ITerm.parent` attribute. The main reason is to make
the :term:`query object` closer to the syntactical structure of the
:term:`expression <query expression>`.

:XEP: 1 -- Simpler :class:`xotl.ql.interfaces.ITerm` interface
:Status: Draft, Incomplete!
:Author: Manuel Vázquez Acosta
:Branch: translation
:Affects: API (and implementation)

Rationale
=========

Currently, the interface for ``ITerm`` has a ``parent`` attribute. That
attribute relates a term to another in the same way a ``getattr`` operation
would do.

So it may be argued that this is actually an operation expressed by the *dot*
operator, and not a term hierarchy. In fact, at the syntactical level there's
no such thing as a parent-child hierarchy for terms; just a ``<term> DOT
<term>`` is present at that level.

This XEP proposed that the expression::

    parent.child

Be represented equivalently to::

   getattribute(parent, 'child')


Inclusion rationale
===================

Changes in the API
------------------

There are two changes in the API:

- The removal of ``parent`` since it won't be needed any more.
- The generalization of :class:`xotl.ql.interfaces.IGeneratorToken` to support
  expressions.

Currently a translator must have a look-up table from token's terms to current
objects (names); and must take into account that every term in filters is bound
to a token.

Let's see how this might work in a relational setting for the query::

  these(child
        for parent in this
	if parent.children & parent.age > 34
	for child in parent.children
	if child.age < 6)


Non-inclusion rationale
=======================

The current implementation complies better with an :term:`AST` than resorting
to transform the `DOT` into a `getattribute`.

If a :term:`translator <query translator>` is best understood (or implemented)
by doing that transformation, it may do so internally.

It's probably easier with current ITerm to see if we need to correlate two
terms (i.e emitting a JOIN in a SQL query) by looking at the term's
parents. And it should not be complicated to know how to fetch an attribute
from, given that binding is inherited from parents.

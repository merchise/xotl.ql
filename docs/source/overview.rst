.. _overview:

========
Overview
========

A running system often needs to retrieve objects from a single or
several sources.

The `xotl.ql` package comprises two main components: the
:ref:`expression language <expression-lang>` and the :ref:`query
language <query-lang>` itself.

The expression language just allows to form expressions using common
operations. The resultant "expressions" are actually python objects
that represent the :term:`expression tree`. As usual, the inner nodes
of the expression tree represents operations and the leaves have the
operands.

The expression language is fairly extensible as you may introduce new
:term:`function object operators <function object operator>`. How to
do is explained later in :ref:`extending-expressions-lang`.

The query language relies heavily on the expression language, since it
allows to express predicates on the objects. The query language itself
is just a combination of:

- the expression language used inside Python's generator expressions
  and/or dictionary comprehensions;
- the :data:`~xotl.ql.core.this` object; and
- the :func:`~xotl.ql.core.these` function.

Let's see a query::

  >>> from xotl.ql import this, these
  >>> parents = these(parent for parent in this
  ...                    if parent.children)



=======================================================
Internal details of the processing of query expressions
=======================================================

This document tries to explain how it's implemented the "parsing" of a
:term:`query expression` into a :term:`query object`.

When processing a query expression, all that is passed to the
:class:`~xotl.ql.core.these` callable is a comprehension (and possible some
keyword arguments that are irrelevant for the purposes of this description.)
We're not in control of how Python does the job of interpreting the real
query expression.

We may try to picture this process, by figuring we have a machine that receives
"events".

Let's use a given query for our purposes::

  these((person.name, partner.name)
        for person in this('person')
	for partner in this('partner')
	for rel in this('relation')
	if rel.type == 'partnership'
	if (rel.subject == person) & (rel.object == partner))

Iterating over `this` should always yield a single :class:`term
<xotl.ql.interface.ITerm>` instance, that may be then placed inside
expressions. So, the only thing that :class:`~xotl.ql.core.these` is in control
of is calling ``next()`` with the comprehension as its argument. This single
call, will start the "machine" and Python itself will be calling methods that
we should trap and interpret as events.

Let's see how Python acts, and how we react.

- When `these` calls ``next(comprehension)``, Python calls the `__iter__`
  method of ``this('person')``.

  This method creates a :term:`generator token` and associates the term
  ``this('parent')`` to the token, then it also builds an instance of
  :class:`xotl.ql.interfaces.IQueryPart`, with
  :attr:`~xotl.ql.interfaces.IQueryPart.expression` assigned to
  ``this('parent')`` and :attr:`~xotl.ql.interfaces.IQueryPart.token` assigned
  to the created `generator token`.

  In this document we will use the notation `tk<expr>` to represent the
  generator token built by the the expression `expr`; and `qp<expr>` to
  represent a query part with ``expression`` equal to `expr`. In both cases,
  we'll use the name of term instead of the full `this(name)`.

  The created query part is yielded.

- Python now calls the `__iter__` method of ``this('partner')``, this will
  create the token `tk<partner>` and the query part `qp<partner>`; this query
  part is yielded.

- Again, Python calls the `__iter__` method of ``this('relation')``, which
  build `tk<relation>` and yields `qp<relation>`.

  At this point it's Python, not our program, who has the handle of these three
  query parts, and they have references to their corresponding tokens.

- Now Python beings to process the `ifs`. The comprehension-local variable
  ``rel`` refers to the query part `qp<relation>`. So, when trying to get
  ``rel.type``, Python calls the `__getattribute__` method of the query part
  `qp<relation>`, who delegates the call to ``this('relation')`` and then wraps
  the result into another query part `qp<relation.type>` -- this new query part
  shares the token `tk<relation>` with `qp<relation>`.

  Also the token `tk<relation>` is notified about the new query part.

  Finally `qp<relation.type>` is returned (to Python).

- Now Python calls the `__eq__` method of `qp<relation.type>` and passes the
  string ``'partnership'`` as a single position argument.

  The query part, delegates the `__eq__` call to
  ``this('relation').type``. This returns the :term:`expression tree`
  ``eq(this('relation').type, 'partnership')``. Now we create another query
  part `qp<eq(relation.type, 'partnership')>`, notify the token `tk<relation>`
  that this part is created and return it (to Python).

- Since Python knows that the `if` wholly processed it moves to the second `if`
  (cause it regards query parts as True)

  .. note::

     At this point our program does not know that the `if` has finished, since
     it's Python who has the control of how the expression is parsed, not us.


- .. _five-steps:

  Python, following it's priority rules, determines that it will run the
  following steps:

  1. ``qp<relation>.subject``
  2. ``operator.eq(1., qp<person>)``

     meaning the it will process as if calling the function ``operator.eq``
     with the result of step 1. as its first argument and `person` as the
     second. See the module :ref:`operator <module-operator>` of the standard
     library.

  3. ``qp<relation>.object``
  4. ``operator.eq(3., qp<partner>)``
  5. ``operator.and_(2., 4.)``

  The steps 1. and 3. are quite similar to how the `rel.type` is processed. For
  the step 2. notice that the first argument is `qp<relation.subject>`, so
  Python invokes the method `__eq__` of this query part with `qp<person>` as
  its argument.

  The query part notices that this argument is also a part and extracts its
  :attr:`~xotl.ql.interfaces.IQueryPart.expression` (in this case
  ``this('person')``) before proceeding. Then it delegates the
  ``operator.eq()`` to its own `expression` (``this('relation').subject``) with
  ``this('person')`` as the second argument.

  The result is wrapped inside a new query part `qp<eq(relation.subject,
  person)>`. Both tokens `tk<relation>` and `tk<person>` are notified of this
  newly created part, and both tokens are appended to the
  :attr:`xotl.ql.interfaces.IQueryPart.tokens` of the resultant query part.

  The query part is returned.

- After Python does the previously sketched steps, it now turns its attention
  to building the *selection* ``(person.name, partner.name)`` tuple.

  .. note::

     Once again our program has no idea that all the `ifs` are done, and that
     it will now be asked to build *selection* expressions.


Depiction of the "machine"
==========================




Flaws of the current implementation
===================================

- [2012-10-30] It may discard filters and tokens that **are** relevant to the
  query object. There's a regression test that shows this bug.

  Although our depiction is based on a "machine"-like object that receives
  events, in our implementation there's no such machine. Maybe if I introduce
  an object that keeps tracks of all events in a single processing of a query
  expression this bug may be easier to fix. Also we may not need to record
  `token` in query parts but such a machine.

  This is tricky, though. Separate events are "collapsible". For instance, the
  five steps described :ref:`above <five-steps>` are separate events, but they
  are collapsed into a single expression filter.



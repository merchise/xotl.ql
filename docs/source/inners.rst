=======================================================
Internal details of the processing of query expressions
=======================================================

This document explains how it's implemented the "parsing" of a :term:`query
expression` into a :term:`query object`. It's a rather technical document and
does not belong to the API, so you may not read it unless you are interested in
the internal implementation of :mod:`xotl.ql.core`.

Restrictions and goals of the procedure for constructing query objects
======================================================================

When processing a query expression, all that is passed to the
:class:`~xotl.ql.core.these` callable is a comprehension (and possible some
keyword arguments that are irrelevant for the purposes of this
description). The key point is that *we're not in control of how Python does
the job of interpreting the real query expression*.

This is further complicated because there might be several expression inside a
single query expression, and we don't know where they "end". Thus, we can't
trust the expression building mechanism to "store" built expressions, because
at that level there's no need of a "multi-expression" kind of object. In fact,
as an historical note, :class:`~xotl.ql.core.these` was created because we
needed to detect expression boundaries, and specially distinguish expressions
occurring in the selection part of the query from those that occur in filters.

Taking account of this restriction, the task of the `query object builder` is
to get a :term:`structure <query object>` that represents a given :term:`query
expression`. But we should try not to interpret/validate the query neither
syntactically nor semantically. Python's has already done it's job of assuring
that the expression is syntactically correct. Our :mod:`expression language
<xotl.ql.expressions>` will raise exceptions if it finds any errors
(unsupported operators for instance).

The only restriction is that the resultant :term:`query object` should be
syntactically equivalent to the input :term:`query expression`.

As an example let's analyze the following query expression::

  these((person.name, partner.name)
        for person in this('person')
	for partner in this('partner')
	for rel in this('relation')
	if rel.type == 'partnership'
	if (rel.subject == person) & (rel.object == partner))


For this query expression, the query object object should:

- Have for :attr:`~xotl.ql.interfaces.IQuery.tokens` the ones related to
  `this('person')`, `this('partner')` and `this('relation')`.

- Have for :attr:`~xotl.ql.interfaces.IQuery.selection` the tuple that contains
  the expressions `person.name` and `partner.name`.

  In these expressions, `person` is actually the term `this('person')`, and
  `partner` is actually the term `this('partner')`

  We'll cover the difference (and relation) of terms and tokens :ref:`later
  <terms-vs-tokens>`.

- Have for :attr:`~xotl.ql.interfaces.IQuery.filters` a list which contains:

  - the expression `rel.type == 'partnership'`, where `rel` stands for the term
    `this('relation')`

  - the expression `(rel.subject == person) & (rel.object == partner)`, the
    terms are the same as before.

If, instead, the query expression were::

  these((person.name, partner.name)
        for person in this('person')
	for partner in this('partner')
	for rel in this('relation')
	if rel.type == 'partnership'
	if rel.subject == person
	if rel.object == partner)

Although it is semantically equivalent to the previous one, its query object
should *not* be the same; for the query expression "parser" must *not* deal
with that kind of equivalence: this query expression is *not* syntactically
equivalent to the previous one. So, the attribute `filters` changes to a list
of:

  - the expression `rel.type == 'partnership'`
  - the expression `rel.subject == person`
  - the expression `rel.object == partner`

.. _terms-vs-tokens:

Terms versus Tokens
===================

As pointed before, there's subtle distinction between terms and tokens. In
previous alpha versions of `xotl.ql`, we used to think that a given term in a
query object should be related to an object generated from a token if that term
was on the list of tokens (or the term's
:attr:`~xotl.ql.interfaces.ITerm.parent` was a token). But this approach was
fundamentally flawed.

The main reason is that a collection may have attributes itself that are
different from those attributes of the objects it yields.

Let's make our point clearer by inspecting the query object expressions
corresponding to::

  these((parent, child)
        for parent in this('parent')
	if parent.children & parent.children.updated_since(1)
	for child in parent.children
	if child.age < 6)

The corresponding query object have:

- two tokens: ``this('parent')`` and ``this('parent').children``
- and two filters:

  - ``this('parent').children & this('parent').children.updated_since(1)``
  - ``this('parent').children.age < 6``

Why does in the expression ``child.age < 6`` "mutates" to
``this('parent').children.age < 6``. Because, the `__iter__` method of a term (like
``this('parent').children``) yields a `query part` that wraps the very term,
and since ``parent.children`` is actually ``this('parent').children``, then
``child`` is just a query part that wraps that term.

Then, how could we tell that ``this('parent').children.updated_since(1)`` is a
condition over the collection ``this('parent').children`` instead over each
object drawn from it? How do we tell that ``this('parent').children.age < 6``
is a condition over objects from and not a condition over the collection
itself?

The answer is simple: terms that occur in expressions of a query object, are
usually :class:`bound <xotl.ql.interfaces.IBoundTerm>` to a generator token. If
we were to explore the terms that occurs in the filters before, we would find
that the term ``this('parent').children.updated_since`` is bound to the
``this('parent')`` token; and the term ``this('parent').children.age`` is bound
to the token ``this('parent').children``. Thus we can precisely determine to
which object a term refers.

.. _free-terms:

"Free" terms
------------

Sometimes when query expressions involve :term:`functions <function object
operator>` like :class:`all_ <xotl.ql.expressions.AllFunction>` that may take
"free" expressions as arguments, terms in that expressions are not
bound. Furthermore, the query object building machinery does not even realizes
those term were there.

.. todo::

   This issue points to another complex issue. Let's analyze the following
   query::

     these(parent for parent in this('parent')
           if any_(child for child in parent.children if child.age < 6))

   Currently, the query object returned contains a single filter that reflects
   the ``any_(...)`` condition; but the argument is unprocessed: a blind
   `generator object`.

   This is partially correct, since if were to "open" the generator, then the
   parts and tokens emitted by this subquery would merge with the ones of the
   outer queries and would lead to an mistaken query object. On the other hand,
   not opening it left *too much* work for :term:`translators <query
   translator>` that actually belongs to the `query object` building machinery.

   If we were to "open" subqueries, the
   :class:`xotl.ql.interfaces.IQueryObject` should be changed to have,
   possibly, an attribute ``queries``; and :class:`xotl.ql.core.these` would
   have to chose a given interpretation of `any_`.

   Also, if we give the responsability to ``these`` we may hurt the extension
   point, since ``these`` not have any knowledge of "future" operations.

   The tie breaker seems to provide a mechanism for resolving generator
   arguments:

   If an operator have implements a given protocol (a subquery protocol), then
   invoke it to produce subqueries. This operator may call ``these``
   recursively to obtain the sub-query, this would have the effect of isolating
   the sub-query elements from the outer queries, and if those subqueries enter
   also have sub-queries, they will be constructed as well.

   Furthermore, leaving this resolution mechanism to operators, leaves open the
   possibility to multiple interpretations.


Notation
========

Before proceeding, let's introduce some notations to keep our explanation more
compact:

- we will use the notation `tk<expr>` to represent the generator
  token built by the the expression `expr`;

- and `qp<expr>` to represent a query part with its
  :attr:`~xotl.ql.interfaces.IQueryPart.expression` equal to `expr`.

- In both cases, we'll use the `name of term` instead of the full `this(name)`
  when a term occurs in an expression.

So `tk<parent>` represents a token created with ``this('parent')``, and
`qp<parent.age > 34>` is a query part that wraps the expression
``this('parent').age > 34``. To keep the notation simple, will identify a bound
term with is :attr:`~xotl.ql.interfaces.IBoundTerm.binding`; so in the query
part `qp<child.age < 6>`, the term `child.age` is bound to the token from which
`child` is drawn.


How does :class:`~xotl.ql.core.these` builds a query object?
============================================================

When creating a query object, :class:`xotl.ql.core.these` creates a stack of
"particles bubbles" [#bubble]_ before drawing any object from the generator
object (i.e before calling `next` to the generator object). The bubble captures
every expression and token that are emitted in the making of expressions that
happen inside the query expression.

Let's see how the whole thing works by looking at how it would process the
following query expression::

  these((person.name, partner.name)
        for person in this('person')
	for partner in this('partner')
	for rel in this('relation')
	if rel.type == 'partnership'
	if (rel.subject == person) & (rel.object == partner))


When the shown sentence is executed, Python creates a `generator object` and
invokes the callable ``these`` with the generator as its sole argument. Then
the following steps are performed in the given order:

1. An instance of a :class:`~xotl.ql.interfaces.IQueryParticlesBubble` is
   created, and is pushed to a :term:`thread-local <thread-local object>` stack
   of bubbles.

2. Then `these` calls ``next(comprehension)``, and then Python calls the
   `__iter__` method of ``this('person')``.

   This method creates the token `tk<person>` and bounds the term to it. This
   token is emitted and captured by the top-most bubble in the thread-local
   stack.

   Then it also builds the query part `qp<person>` and yields it. This query
   part is not emitted because `__iter__` knows it won't make any sense.

3. Python now calls the `__iter__` method of ``this('partner')``, this will
   create the token `tk<partner>` and the query part `qp<partner>`; this query
   part is yielded. Again only the token `tk<partner>` is emitted and captured
   by the bubble.

4. Once more, Python calls the `__iter__` method of ``this('relation')``, which
   build `tk<relation>` and yields `qp<relation>`. The bubble captures the token
   `tk<relation>`.

   At this point it's Python, not our program, who has the handle of these
   three query parts. But our bubbles has captured all the tokens.

5. Now Python beings to process the `ifs`. The comprehension-local variable
   ``rel`` refers to the query part `qp<relation>`. So, when trying to get
   ``rel.type``, Python calls the `__getattribute__` method of the query part
   `qp<relation>`, who delegates the call to its contained
   :attr:`~xotl.ql.interfaces.IQueryPart.expression` which is
   ``this('relation')``, and then wraps the result into another query part
   `qp<relation.type>` and emits the query part (and is captured by the
   bubble.)

   Finally `qp<relation.type>` is returned (to Python).

6. Now Python calls the `__eq__` method of `qp<relation.type>` and passes the
   string ``'partnership'`` as its sole positional argument.

   The query part, delegates the `__eq__` call its contained expression
   ``this('relation').type``. This returns the :term:`expression tree`
   ``eq(this('relation').type, 'partnership')``. Now we create another query
   part `qp<eq(relation.type, 'partnership')>`, and emit it.

   The bubble realizes that this newly emitted query part's expression
   *contains* (see
   :meth:`~xotl.ql.interfaces.IQueryParticlesBubble.capture_part`) the
   previously captured expression ``this('relation').type``; so it forgets
   about this "contained" expression, and just keep the bigger one.

   We then return the query part `qp<eq(...)>` (to Python).

7. Since Python knows that the first `if` is entirely processed it moves to the
   second `if` (cause it regards the returned query part as True).

   .. note::

      At this point our code does not know that the `if` has finished, since
      it's Python who has the control of how the expression is parsed, not us.

8. .. _five-steps:

   Python, following it's priority rules, determines that it will run the
   following steps:

   1. Compute `qp<relation>.subject`, by calling `__getattribute__` to
      `qp<relation>`.

   2. Compute ``operator.eq(``\ **1.**\ ``, qp<person>)``

      meaning it will proceed as if calling the function ``operator.eq`` with
      the result of step 1. as its first argument and `qp<person>` as the
      second. See the module :ref:`operator <module-operator>` of the standard
      library.

   3. Compute ``qp<relation>.object``

   4. Compute ``operator.eq(``\ **3.**\ ``, qp<partner>)``

   5. An finally compute ``operator.and_(``\ **2.**, **4.**\ ``)``

   The steps 1. and 3. are quite similar to how the `rel.type` is
   processed. For the step 2. notice that the first argument is
   `qp<relation.subject>`, so Python invokes the method `__eq__` of this query
   part with `qp<person>` as its argument.

   The query part notices that this argument is also a part and extracts its
   :attr:`~xotl.ql.interfaces.IQueryPart.expression` (in this case
   ``this('person')``) before proceeding. Then it delegates the
   ``operator.eq()`` to its own `expression` (``this('relation').subject``)
   with ``this('person')`` as the second argument.

   The result is wrapped inside a new query part `qp<eq(relation.subject,
   person)>`. The created query parts are all emitted, and captured by our
   bubble, and upon capture they are inspected to find out if they *contain*
   previously emitted parts, and if they do, only the bigger ones are kept.

   The query part is returned.

9. After Python does the previously sketched steps, it now turns its attention
   to building the *selection* ``(person.name, partner.name)`` tuple.

   .. note::

      Once again our program has no idea that all the `ifs` are done, and that
      it will now be asked to build *selection* expressions.

   Again, Python calls `__getattribute__` to `qp<person>` to get its `name`
   attribute; this call creates yet another part emits that query part. Since
   that query part does not contain any previously emitted part (actually,
   since we use *is* comparison there will never be a case in which parts that
   occur in different syntactical units are confused although they may be
   equivalent -- i.e different `ifs`, or different elements in the selection
   won't be merged and thus their boundaries will be established.)

   Then, Python calls `__getattribute__` to `qp<partner>` to get its `name`
   attribute. Again, the part is emitted.

10. Now the `next(comprehesion)` returns the tuple. If we were to call `next`
    again it would raise a StopIteration exception, since
    :meth:`xotl.ql.interfaces.ITerm.__iter__` should yield a single query part.

11. :func:`~xotl.ql.core.these` now regains control and it pops top-most bubble
    from thread-local stack. If we inspect its
    :attr:`~xotl.ql.interfaces.IQueryParticlesBubble.parts` we'll find the
    following expressions in the given order:

    1. ``relation.type == 'partnership'``, where the term `relation.type` is
       bound to `tk<relation>`.

    2. ``(relation.subject == person) & (relation.object == partner)``, where
       the terms `relation.*` are bound to `tk<relation>`, the term `person` is
       bound to `tk<person>` and the term `partner` is bound to `tk<partner>`.

    3. ``person.name``

    4. ``partner.name``

12. Now :func:`~!xotl.ql.core.these` inspect the tuple of selected expressions,
    and if they are at the end of the captured parts in the bubble, those parts
    are disregarded.

13. Finally, the :term:`query object` is created and the selections are simply
    assigned, the :attr:`~xotl.ql.interfaces.IQueryObject.tokens` are those
    captured by our bubble, and the captured parts are assigned to the
    attribute :attr:`~xotl.ql.interfaces.IQueryObject.filters`.

    .. Before returning the query, `these` post-process each filter by walking its
    .. expression tree, and invoking the :ref:`sub-queries protocol
    .. <subquery-protocol>`.

Footnotes
=========

.. [#bubble] Particles bubbles are used by experimental physicists to capture
	     sub-atomic particles. Our particle is either a token or an
	     expression, and our bubble captures them all and stores them so
	     that we are able to create the query object from those pieces (and
	     their order).

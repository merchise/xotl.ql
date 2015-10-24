.. _monads:

======================
 Monads Comprehension
======================

.. automodule:: xotl.ql._monads


Algebra operator as abstractions
================================

To stress the idea of abstraction of algorithms notice that engines may
proceed differently to obtain the result of |map f l|.

If we can sensibly split `l`:math: into `l_1, l_2, ..., l_n`:math: then:

  .. math::

     {\bf map}_f l = {\bf map}_f (l_1 \oplus l_2 \oplus{} ... \oplus l_n) = \
     {\bf map}_f {\bf join}([l_1, l_2, ..., l_n]) = \
     {\bf join}([{\bf map}_f l_1, {\bf map}_f l_2, ..., {\bf map}_f l_n])


In fact, many times `l`:mathvar: is actually stored in chunks; it may be
stored distributed across several nodes or in a single node but split in
several size-bounded buckets.

Therefore, instead of getting all the pieces of `l`:mathvar: and then
performing the map over the entire collection, we can perform the map over the
pieces and then join them to get the result.  The engine can make any choice
it thinks it's the best.

.. |map f l| replace:: `{\bf map}_f l`:math:

Refer to [MCQL]_ for more about catamorphisms and `catamorphism fusion`.  See
note on `foldr-notation`:ref:.


Internal representation
=======================

.. autoclass:: Empty()

.. class:: Cons(x, xs)

   This is an *abstract* representation of the "|x:xs|" operation as referred
   in [QLFunc]_.  It's not meant to be efficient or to be used as true
   collection for Python programs.

   The `xs` must be a *collection* or another `Cons` object.  If a collection
   is passed it will be converted to a `Cons` object.

   There's no built-in concept of *equality* or equivalence since that would
   require a specific type.  The proposition::

     Cons(1, Cons(2, Empty())) == Cons(2, Cons(1, Empty()))

   would be True for sets and bags but not for lists.

   Cons support the extraction of head and tail we see in functional
   languages::

     >>> head, tail = Cons(1, [2, 3])
     >>> head
     1

     >>> tail
     Cons(2, Cons(3, Empty()))

   Notice that unless you build the structure with `Cons` itself it may not be
   well defined the value of the head::

     >>> _, (head, tail) = Cons(1, {128, 90})   # Is head 128 or 90?

   There's no direct support for walking the `Cons` besides its ability to
   extract the head and tail.  Walking is easily defined by recursion or
   iteration::

     >>> def walk(c):
     ...    h, t = c
     ...    yield h
     ...    if t:
     ...        for i in walk(t):
     ...            yield i

     >>> list(walk(Cons(1, [2, 3])))
     [1, 2, 3]

     >>> def walk(c):
     ...    h, t = c
     ...    while t:
     ...       yield h
     ...       h, t = t
     ...    yield h

     >>> list(walk(Cons(1, [2, 3])))
     [1, 2, 3]

   Any of the arguments may take the value be `xoutil.Undefined`:obj: to
   "partialize" the constructor.  Using this feature you may declare the
   monadic Unit operator as::

     >>> from xoutil import Undefined
     >>> Unit = Cons(Undefined, [])

   And then use it like::

     >>> Unit(1)
     Cons(1, Empty())


.. class:: Foldr(operator, initial, collection)

   `foldr` is defined by:

   .. math::
      :nowrap:

      \begin{eqnarray}
         {\bf foldr}^\tau & :: & (\alpha \rightarrow \beta \rightarrow \beta)
             \rightarrow \beta \rightarrow \tau\  \alpha \rightarrow \beta \\

             \\

         {\bf foldr}^\tau (\oplus) z []^\tau & = & z \\

         {\bf foldr}^\tau (\oplus)\ z\ (x :^\tau xs) & = & x \oplus
            ({\bf foldr}^\tau (\oplus)\ z\ xs)
      \end{eqnarray}


   The `foldr` operation is also known as the `reduce` function.  In fact
   ``Foldr(func, initial, coll)()`` returns the same result as
   ``reduce(func, coll.asiter(), initial)``::

       >>> import operator
       >>> Foldr(operator.add, 0, Cons(1, [2]))()
       3

       >>> reduce(operator.add, Cons(1, [2]).asiter(), 0)
       3

       # Want to pass a `Cons` to `reduce`? Use `Foldr`:
       >>> reduce(Foldr(operator.add, 10), Cons(1, [2]))
       3

   As noted in [QLFunc]_ the `Cons`:class: operator (|:|) needs to be further
   specified for *set* and *bags*.  Also the "|+|" infix operator needs to be
   commutative if |:| is left-commutative and idempotent if |:| is
   left-idempotent.

   For the purposes of `xotl.ql` this class is only meant for description and
   not functionality.  So these questions are not directly addressed.


.. autoclass:: Union(xs, ys)


Sorting
-------

Sorting is only sensibly defined over lists.  Our `Cons`:class: constructor
can be regarded as a list constructor.  The problem of sorting a list can be
defined with `Foldr`:class: as well.

We simply need to define the |x:<xs| operator that inserts `x` into `xs` in
the "right" position.

|x:<xs| is easily defined as:

.. math::
   :nowrap:

   \begin{eqnarray}
      :^\tau_< \quad & :: & \alpha \rightarrow \tau\alpha \rightarrow \tau\alpha \\
      \\
      x :^\tau_< [] & = & x :^\tau [] \\
      x :^\tau_< (y :^\tau_< ys)  & = & {\bf if}\, x < y\,\,
                                        {\bf then}\, x :^\tau (y :^\tau_< ys)\,\,
                                        {\bf else}\, y :^\tau (x :^\tau_< ys)
   \end{eqnarray}

Now sorting can be achieved by:

.. math::

   {\bf sort}^\tau_< = {\bf foldr} :^\tau_< []


Defining |:>| is just as easy, and then `{\bf sort}^\tau_>`:math: can be
defined as well.

Sorting is only well defined if `<`:math: (or `>`:math:) are also properly
defined.

Yet, sorting can be expensive and engines are allowed to take shortcuts.  For
instance, Google's MapReduce [MAPRED]_ always sort the result of a map by
`keys` (all values in Google's MapReduce are a pair of ``key, value``.)

Nevertheless, it can be useful to include sorting in our algebraic definition
so that ordering instruction can be explicitly represented.

Notice, however, Python generator expressions don't directly support
expressing ordering.  Other query languages like SQL do support them.


.. autoclass:: SortedCons(order)

   `SortedCons`:class: won't sort a list.  It will simply "push" its first
   argument until it matches the `order` function::

      >>> SortedCons('<')(49, Cons(30, Cons(50, Cons(10, [-1]))))
      Cons(30, Cons(49, Cons(50, Cons(10, Cons(-1, Empty())))))

   Using `Foldr` we obtain a sort function::

     >>> Foldr(SortedCons('<'), Empty())(Cons(30, Cons(49, Cons(50, Cons(-1, Empty())))))
     Cons(-1, Cons(30, Cons(49, Cons(50, Empty()))))

     >>> Foldr(SortedCons('>'), Empty())(Cons(30, Cons(49, Cons(50, Cons(-1, Empty())))))
     Cons(50, Cons(49, Cons(30, Cons(-1, Empty()))))




.. |+| replace:: `\oplus`:math:
.. |:| replace:: `:^\tau`:math:
.. |x:xs| replace:: `x :^\tau xs`:math:

.. |x:<xs| replace:: `x :^{\tau}_{\small <} xs`:math:
.. |:<| replace:: `:^{\tau}_{\small <}`:math:
.. |:>| replace:: `:^\tau_>`:math:



Memento for mathematical terms
==============================

.. glossary::

   monoid

      An algebraic structure with an *associative* operator `++` having a
      distinguished element *zero* (`0`) as left and right identity::

        0 ++ x = x
        x ++ 0 = x

      https://en.wikipedia.org/wiki/Monoid

      I don't know why in [MCQL]_ they claim `([], :)` is a monoid.
      Presentation of a monoid.

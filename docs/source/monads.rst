.. _monads:

======================
 Monads Comprehension
======================

Internal representation
=======================

.. module:: xotl.ql._monads

.. autoclass:: Empty()

.. class:: Cons(x, xs)

   This is an *abstract* representation of the "|x:xs|" operation as referred
   in [QLFunc]_.  It's not meant to be efficient or to be used as true
   collection for Python programs.  Furthermore, though it may seem like a
   list implementations of bags and sets should also be possible.

   It serves the purpose of expressing queries and it will form the basic
   building block for the `query object`:term:.

   The `xs` must be a *collection* or another `Cons` object.  If a collection
   is passed it will be converted to a `Cons` object.

   There's no built-in concept of *equality* or equivalence since that would
   require a specific type.  The proposition::

     Cons(1, Cons(2, Empty())) == Cons(2, Cons(1, Empty()))

   would be True for sets and bags but not for lists.

   Instances support the extraction of head and tail we see in functional
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


   The `foldr` operation is a generalization of the `reduce` function.  It
   operates as illustrated below::

                       +
                      / \
                     x1  +
                        / \
                      x2   z

   As noted in [QLFunc]_ the `Cons`:class: operator (|:|) needs to be further
   specified for *set* and *bags*.  Also the "|+|" infix operator needs to be
   commutative if |:| is left-commutative and idempotent if |:| is
   left-idempotent.

   For the purposes of `xotl.ql` this class is only meant for description and
   not functionality.  So these questions are not directly addressed.


.. |+| replace:: `+`:math:
.. |:| replace:: `:^\tau`:math:
.. |x:xs| replace:: `x :^\tau xs`:math:

.. _monads:

======================
 Monads Comprehension
======================

.. math::
   :nowrap:

   \begin{eqnarray}
      {\bf foldr}^\tau & :: & (\alpha \rightarrow \beta \rightarrow \beta)
          \rightarrow \beta \rightarrow \tau \alpha \rightarrow \beta \\
      {\bf foldr}^\tau (\oplus) z []^\tau & = & z \\
      {\bf foldr}^\tau (\oplus)\ z\ (x :^\tau xs) & = & x \oplus
         ({\bf foldr}^\tau (\oplus)\ z\ xs)
   \end{eqnarray}



Internal representation
=======================

.. module:: xotl.ql._monads

.. autoclass:: Empty()

.. autoclass:: Cons(x, xs)

   This is an *abstract* representation of the "x : xs" operation as referred
   in [QLFunc]_.  It's not meant to be efficient or to be used as true
   collection for Python programs.  Furthermore

   It serves the purpose of expressing queries and it will form the basic
   building block for the `query object`:term:.

   The `xs` must be a *collection* or another `Cons` object.

   Instances support the extraction of head and tail we see in functional
   languages::

     >>> head, tail = Cons(1, [2, 3])
     >>> head
     1

     >>> tail
     Cons(2, Cons(3, Empty()))

   Any of the arguments may take the value be `xoutil.Undefined`:obj: to
   "partialize" the constructor.  Using this feature you may declare the
   monadic Unit operator as::

     >>> from xoutil import Undefined
     >>> Unit = Cons(Undefined, [])

   Then building the "unit" can be done::

     >>> Unit(1)
     Cons(1, Empty())

   There's no direct support for walking the `Cons` besides its ability to
   extract the head and tail.  Walking is easily defined by recursion or
   iteration::

     >>> def last(c):
     ...    h, t = c
     ...    return h if not t else last(t)

     >>> last(Cons(1, [2, 3]))
     3

     >>> def last2(c):
     ...    h, t = c
     ...    while t:
     ...       h, t = t
     ...    return h

     >>> last2(Cons(1, [2, 3]))
     3

   Internally the head is the attribute `x` and the tail, attribute `xs`.

.. autoclass:: Foldr(f, z, l)

   The `foldr` operation is a generalization of the `reduce` function.  It
   operates as illustrated below::

                       +
                      / \
                     x1  +
                        / \
                      x2   z

   As noted in [QLFunc]_ the `Cons`:class: operator (:math:`x :^\tau xs`)
   needs to be further specified for *set* and *bags*.

   However, for the purposes of `xotl.ql` this is only meant for description
   and not functionality.

==========================
 Just another scratch pad
==========================

Notes on [Burstall1977]_
========================

- Laws.  Well expressed as *known properties* about the objects.
  Associativity, commutativity, etc..

  a) ``i + j`` --- Does not commute on strings, but it does associate.

  b) ``A * M`` --- Commutes if A is a scalar and M a matrix, but does not
     commute if both are matrices.  It associates for scalars and matrices
     alike being mixed.

  In xotl.ql, this kind of information can be only provided by
  `isinstance`:func: inside a `query expression`:term:, or by the object
  model (known only to the `translator`:term:).


Notes on [MCQL]_
================

- Catamorphims.  They express the property of the spine transformers as::

    (z; +) ⋅ cata n c  =  cata z +

  being ``+`` the general list-appending (or set/multiset member inclusion).

  This means that if we can prove ``cata`` a catamorphim, we can optimize by
  applying it to results.


.. LocalWords: Catamorphims

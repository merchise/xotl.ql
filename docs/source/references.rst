============
 References
============

.. [UnQL] Peter Buneman, Susan Davidson, Gerd Hillebrand, and Dan Suciu.  "A
   Query Language and Optimization Techniques for Unstructured Data".
   http://citeseerx.ist.psu.edu/viewdoc/summary?doi=10.1.1.33.2802
   http://dl.acm.org/citation.cfm?id=233368
   http://homepages.inf.ed.ac.uk/opb/papers/SIGMOD1996.pdf


.. [coSQL2011] Erik Meijer and Gavin Bierman.  "A co-Relational Model of Data
   for Large Shared Data Banks", Comm. ACM, 54(4) April 2011.
   http://queue.acm.org/detail.cfm?id=1961297

.. [coSQL2012] Maarten Fokkinga.  "SQL versus coSQL — a compendium to Erik
   Meijer's paper", Jan 2012.
   http://wwwhome.ewi.utwente.nl/~fokkinga/mmf2011p.pdf

.. [MCQL] Torsten Grust.  "Monads Comprehensions: A Versatile Representation
   for Queries".  University of Konstanz, Department of Computer and
   Information Science, 78457 Konstanz, Germany.

.. [Peyton1987] Peyton, Simon.  "The Implementation of Functional Programming
   Languages".  Prentince-Hall, 1987.  Available at:
   http://research.microsoft.com/en-us/um/people/simonpj/papers/slpj-book-1987/start.htm

.. [Burstall1977] Bustall, R and Darlington, John.  "A Transformation System
   for Developing Recursive Programs".  Journal of the Assooat~on for
   Computing Machinery, Vol 24, No 1, January 1977, pp. 44-67.  Available at:
   http://citeseerx.ist.psu.edu/viewdoc/summary?doi=10.1.1.19.4684

.. [QLFunc] Torsten Grust and Marc H. Scholl.  "How to comprehend queries
   functionally". University of Konstanz, Department of Computer and
   Information Science, 78457 Konstanz, Germany.

.. [MAPRED] Dean, Jeffrey and Ghemawat, Sanjay.  "MapReduce: Simplified Data
            Processing on Large Clusters".  Google Inc.  Available at ...



Notes
=====

.. _foldr-notation:

foldr notation
--------------

.. [#foldr_notation] Notational differences for the same concept: whereas in
   [QLFunc]_ we see `{\bf foldr}^\tau (\oplus)\, z\, []^\tau`:math: in [MCQL]_
   we see `(|\, z; \oplus\, |)`:math:

   We choose a notation that's easy to read in python code comments and
   inlined documentation.  In this documents (specially the parts extracted
   from source code) you'll see ``foldr z +`` and ``(z; +)`` instead.

.. [#monoids]

   Why does [MCQL]_ says `{\small ([], \uparrow)}`:math: is a `monoid`:term:
   if `{\small \uparrow :: a \times [a] \rightarrow [a]}`:math: and `{\small x
   \uparrow [] = [x] \neq x}`:math:?

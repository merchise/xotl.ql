Changelog
=========

2012/12/20 - Release 0.1.8
--------------------------

- Fixed a bug discovered while cleaning up the implementation. Arguments for
  N_ARITY functions where not being properly handled.

  This was fixed actually by simplifying :class:`xotl.ql.core.QueryPart` to
  implement the :ref:`target protocol <target-protocol>` to extract is
  expressions.

- Improves and updates documentation.

- Provides a "wish list" for future releases in :ref:`Next releases goals
  <next-releases-goals>`.


2012/12/18 - Release 0.1.7
--------------------------

- Fixes pending bug that make tests fail randomly. Now this is
  deemed stable enough!

  Start developing translators!

- Proposing to release a version 0.2, to mark the current level
  of maturity.

2012/12/08 - Release 0.1.6
--------------------------

- Fixes several bugs. But there's still pending a non-determinancy
  bug.

- Improved an explanation of internal details of the current
  implementation.

- Starts to comply more closely with PEP8: Use a single blank line to
  separate class-level definitions (we used 2); use two blank lines
  separate module-level definitions.


2012/11/05 - Release 0.1.5
--------------------------

- Huge revamp of design (again). Introduced the metaphor of "particles
  bubble" to capture the query expression most precisely.

  A draft of the description of "Internal details..." is provided.

2012/10/22 - Release 0.1.4
--------------------------

- Huge revamp of design. Now I'm proud to say the query language
  is almost done in its first stage.

  Introduces QueryPart, loads of documentation has been updated.
  Tests for design are now almost done, etc...

  You're encourage to try it!

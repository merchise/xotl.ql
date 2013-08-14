- Updates to the latest xoutil release that introduces changes in
  :mod:`xoutil.context` API.

- A lots of fixes to the :mod:`xotl.ql.translation.py` module. The core
  translation algorithm is now reasonably tested.

  The sub-query interpretation for functions like :class:`all_
  <xotl.ql.expressions.AllFunction>` and other like it, is now implemented and
  partially tested.

  We have also introduced a :ref:`class-level protocol for instances
  <instances-class-protocol>` so that the search space for objects be reduced
  in the hope of making this translator usable for one-user-only, short-lived
  applications.

- Updates to the latest xoutil release that introduces changes in
  :mod:`xoutil.context` API.

- A lots of fixes to the :mod:`xotl.ql.translation.py` module. It is reasonably
  tested.

  We have also introduced a :ref:`class-level protocol for instances
  <instances-class-protocol>` so that the search space for objects be reduced
  in the hope of making this translator usable for one-user-only, short-lived
  applications.

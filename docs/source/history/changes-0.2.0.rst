- Another round of redesign has been completed: The old and clunky QueryPart
  concept was removed, now just expressions, :term:`bound terms <bound term>`,
  and :term:`generator tokens <generator token>` are the needed.

  However a :ref:`new protocol <resolve-arguments-protocol>` was introduced.

- Compatible with Python 3.2 out-of-the-box, no need to use the 2to3
  script.

- **Hooray!** We have now a test-bed :mod:`translator <xotl.ql.translation>`
  partially implemented. It's quite new and under-tested and sub-queries
  functions (like :class:`~xotl.ql.expressions.all_`) are not yet translated.

  Although PyPy is not fully supported, it passes all tests of the core
  language, but fails in the translation. Nevertheless the
  :mod:`xotl.ql.translation.py` is not meant to be used in production.

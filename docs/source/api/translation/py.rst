=====================================================
 `xotl.ql.translation.py`:mod: -- A naive translator
=====================================================

This document servers a double purpose, it's both the documentation of the
translator and also a an example on how other translators are to be
documented.


Introduction
============

.. module:: xotl.ql.translation.py

This module provides a simple and naive `query translator`:term: that uses the
Python object space as its `object model`:term:.  This basically means the
object model matches the Python data model.  You may use any built-in function
and it will behave the same as in any Python program.

Usage
=====

You get an instance of the translator simply by importing the module::

  >>> from xotl.ql.translation import py

The module complies with the interface
`xotl.ql.interfaces.QueryTranslator`:class:::

  >>> from xotl.ql.interfaces import QueryTranslator
  >>> isinstance(py, QueryTranslator)
  True

To translate a query expression simply pass it to the module::

  >>> from xotl.ql.core import this
  >>> get_named_objects = py(
  ...     which for which in this
  ...     if type(which).__module__.startswith('__main__')
  ...     if hasattr(which, 'name')
  ... )

The result a is `NaivePythonExecutionPlan`:class:.  You may iterate over it to
get the results::

  >>> list(get_named_objects)
  []

Afterwards you may create new named objects and the same plan will get them::

  >>> class new(object):
  ...    def __init__(self, **kw):
  ...        self.__dict__.update(kw)

  >>> named1 = new(name='named1')

  >>> named1 in list(get_named_objects)
  True

If you remove the object from the Python process memory it won't be fetched
anymore *after* it's reclaimed by the garbage collector::

  >>> del named1

  >>> import gc
  >>> collected = gc.collect()

  >>> list(get_named_objects)
  []

Notice we can't make any guarantees about whether the object is alive or not.

The translator is usable even for query expressions which don't iterate over
the |this| object::

  >>> get_numbers = py(n for n in range(10))
  >>> list(get_numbers)
  [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]


Interpretation of ``this``
==========================

The default interpretation of any occurrence of |this| as a generator inside a
query expression is *the entire object space* in the current Python process.

If `this` appears as a generator, or is used in a way that iteration occurs,
all objects currently alive in the Python VM will be generated.  The actual
objects generated are obtained using the function `gc.get_objects`:func:.  By
default we omit objects which are instances of any type defined in the
packages:

- ``xotl.ql``
- ``xoutil``
- ``IPython``
- ``py``, i.e. the `py package`_.
- The module for builtins objects (this is the module ``__builtin__`` in
  Python 2.7 and ``builtins`` in Python 3).

If `this` appears as non-generator it will be replaced by an instance of
`PythonObjectsCollection`:class:\ ::

  >>> query = py(this for _ in range(1))
  >>> list(query)   # doctest: +ELLIPSIS
  [<xotl.ql.translation.py.PythonObjectsCollection...>]


Extensions
==========

This translator support the extensions describe by
`xotl.ql.interfaces.QueryTranslatorExplainExtension`:class:.

.. autofunction:: explain


.. _py package: https://pypi.python.org/pypi/py

.. |this| replace:: `~xotl.ql.core.this`:obj:

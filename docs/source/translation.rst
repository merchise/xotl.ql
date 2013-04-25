.. _translation:

=========================
Translating query objects
=========================

Translation is the process that transforms a :term:`query object` into a form
feasible for a :term:`data store <storage>` and/or :term:`object model` to
execute. The result of translating a query object is a :term:`query execution
plan`.

:term:`Query translators <query translator>` are the components responsible for
translation. `xotl.ql` does not provide production quality translators, but
other packages are planned to have implementation of translators. Nevertheless,
the module :mod:`xotl.ql.translation.py` provides an implementation of *naive*
translator that matches the Python object model and fetches objects from the
current process memory.

  *This section is only mostly relevant for translation authors only*. It
  contains details that are not important for application writers. However,
  application writers might profit from these notes in order to better
  understand possible exceptions they are facing.

General requirements about translators
======================================

Re-usability of execution plans
-------------------------------

It is required that translators allow the reuse of execution plans; i.e. once a
query is translated you may execute the plan several times to fetch the objects
that matches the query at the time the plan is executed.

This way one may use the translator only once per query.

In fact :class:`xotl.ql.core.QueryObject` assumes that the :ref:`configured
<translator-conf>` translator abides by this requirement to avoid building the
execution plan several times.


Documentation requirements
--------------------------

Translators authors are encouraged to provide as much documentation as
necessary, so that application writers have the guidance they need for writing
queries.

We feel the following information is *required* in order for a translator
documentation be complete:

- A list of the supported expression operations from the :mod:`xotl.ql
  expression API <xotl.ql.expressions>`.

- A list of additionally supported operations, and their related documentation.

- Documentation of functions, classes applications writers may use to access
  the translator functionality directly if they have to.

- Additional keyword arguments you may pass to their implementation of
  :meth:`~xotl.ql.interfaces.IQueryTranslator.__call__`; the additional
  :attr:`parameters <xotl.ql.interface.params>` you may pass via
  :class:`~xotl.ql.core.these` and how they relate.

- Configuration options you may pass to the translator; and how to instantiate
  a translator with those configurations.

.. _translator-conf:

Configuration of translator
===========================

.. warning::

   This section is still in a very unstable state.

Currently `xotl.ql` makes use of Zope Component Architecture (ZCA)
registration of components to register translators.

There are two interfaces which relate to this:

- :class:`xotl.ql.interfaces.IQueryConfigurator`

- :class:`xotl.ql.interfaces.IQueryTranslator`

The interface IQueryTranslator is just the interface "true" translators should
provide. If you implement a component that performs translation, this should
implement this interface.

The interface IQueryConfigurator allows to get the "current" translator.


Using the Pyramid's registry
----------------------------

If you need (or want) to use the Pyramid's ZCA application registry, you should
use the ``hook_zca()`` of the ``pyramid.config.Configurator`` class, like
this::

    config = Configurator(**settings)
    config.hook_zca()
    config.registry.registerUtility(your_translator, IQueryTranslator)

This is not needed, though. However, you must make sure to register your
translator for each WSGI application instance you have.

It is encouraged that translator authors write mediators that glue their
translator with a given framework. It is also encourage that such mediators be
distributed separately from the translator itself. For instance, you might
write a Pyramid Tween that glues your translator with Pyramid's registry.

..
   For demonstration purposes only, a Pyramid Tween is provided in
   :mod:`xotl.ql.translation.tween` that glues our :mod:`xolt.ql.translation.py`
   translator with Pyramid. To see it in action::

      config.include('xotl.ql.translation.tween')

   And then navigate to '/xotl-ql-demostration/'

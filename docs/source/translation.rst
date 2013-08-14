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

Configuration of an application is *not* one of the goals `xotl.ql`
pursues. That's the job of frameworks. So this section refers only to the small
amount of assumptions `xotl.ql` has about *getting* a configured translator
when it's needed.

Configuration of an entire system is a complex matter. Even deciding *what*
configuration is and what is not is an issue that must be well thought.

That been said, the only place where currently `xotl.ql` does make an
assumption about the configuration is when trying to get an instance of a
:term:`query translator`. This is done exactly only when you try to iterate
over a query object::

  for atom in these(atom for atom in Universe):    # <--- here
      classify(atom)

`xotl.ql` makes use of Zope Component Architecture (ZCA) registration of
components to look for translators.

There are two interfaces which relate to this job:

- :class:`xotl.ql.interfaces.IQueryConfigurator`

- :class:`xotl.ql.interfaces.IQueryTranslator`

When trying to get a translator, `xotl.ql` does the following:

1. First it looks if there is an instance of IQueryConfigurator in the ZCA
   global registry.

   If found, it will call its
   :meth:`~xotl.ql.interfaces.IQueryConfigurator.get_translator` passing the
   query.

2. If there's no configurator then it will try to look for an instance of a
   IQueryTranslator in the global registry.

   If this step also fails a ComponentLookupError exception will be raised.

3. If any of the previous steps does return a translator, then it will be
   called with the current query as its sole positional argument.

   The returned :term:`query execution plan` will be cached by the query object
   to avoid having to look for translator and perform the translation
   again. [#cache]_

If you're not comfortable using ZCA, you avoid at all; just don't iterate
directly over a query object. Translator will probably have APIs for direct
use. For instance, our toy :mod:`~xotl.ql.translation.py` translator provides
the function :func:`~xotl.ql.translation.py.naive_translation` that is the one
that performs the translation. Many of our tests use this function instead of
iterating over query objects.


.. _configurators-best-practices:

Best practices for configurators
--------------------------------

Configurators should follow the motto "be liberal about what you may get"
[#conservative]_. This means that they should make the least amount of
assumptions possible for any argument they might receive.

Here are some ideas:

- If you expect a keyword argument that should contain a class/function and you
  receive a string, try to *load it* as dotted name.

  This is to allow INI configuration files.

- Whenever possible log a BIG warning instead of raising an exception.


Using the Pyramid's registry
----------------------------

If you need to use the Pyramid's ZCA application registry, you should use the
``hook_zca()`` of the ``pyramid.config.Configurator`` class, like this::

    config = Configurator(**settings)
    config.hook_zca()
    config.registry.registerUtility(your_translator, IQueryTranslator)

This is not needed, though. However, you must make sure to register your
translator for each WSGI application instance you have.

It is encouraged that translator authors also write mediators that glue their
translator with a given framework. It is also encouraged that such mediators be
distributed separately from the translator itself. For instance, you might
write a Pyramid Tween that glues your translator with Pyramid's registry.


.. [#cache] This cache is local to the query object, if the later is discarded
	    the plan will also be discarded (unless there's a bug somewhere
	    else, for instance the translator could keep its own cache that is
	    getting too big.)


.. [#conservative] "... and be conservative about what you provide", but, hey!,
		   they are required to return a translator.

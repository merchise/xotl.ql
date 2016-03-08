.. _query-lang:

=====================================
 `xotl.ql.core`:mod: -- The core API
=====================================

.. module:: xotl.ql.core

The module `xotl.ql.core`:mod: provide the high level API for obtaining a
`query object`:term: from a `query expression`:term:.

.. data:: this

   This is an object whose meaning is the *entire universe of objects* when
   used as a generator inside a query expression.  Its precise semantics
   varies with the `object model`:term:.  The documentation of `query
   translators <query translator>`:term: must give the precise meaning of this
   object.

.. autofunction:: get_query_object

   This function expects a `query expression`:term: in the form of a generator
   object and returns an object that complies with the interface
   `xotl.ql.interfaces.QueryObject`:class:.

   :param query:  The query expression.

   :param query_type: An object which complies with the interface
                      `xotl.ql.interfaces.QueryObjectType`:class: or the fully
                      qualified name of such an object.

   :param frame_type: An object with complies with the interface
                      `xotl.ql.interfaces.FrameType`:class: or the fully
                      qualified name of such an object.

   This function works by inspecting the byte-code of the generator object to
   obtain the `Query Syntax Tree`:term:.  This function uses the attribute
   `gi_frame` of the generator to build the frame object needed by query
   objects.

   Nested sub-queries are not expanded automatically::

     >>> from xotl.ql.core import this, get_query_object
     >>> query = get_query_object(y for y in (x for x in this))

     >>> print(query.qst)
     <ast: Expression>
        body: <ast: GeneratorExp>
           elt: <ast: Name>
              id: 'y'
              ctx: <ast: Load>
           generators[0]: <ast: comprehension>
              target: <ast: Name>
                 id: 'y'
                 ctx: <ast: Store>
              iter: <ast: Name>
                 id: '.0'
                 ctx: <ast: Load>

   The sub-query ``(x for x in this)`` is simply encoded as a variable '.0'.
   Provided


   If no `frame_type` is provided, use the attribute
   `~xotl.ql.interfaces.QueryObjectType.frame_type`:attr: of the query object
   type.

   Additional keyword arguments are passed unchanged when instantiating the
   query object.


.. autofunction:: normalize_query

.. class:: QueryObject(qst, frame, **kwargs)

   A query object implementation.

   Instances of this class implement the interface
   `xotl.ql.interfaces.QueryObject`:class: and this class itself complies with
   `xotl.ql.interfaces.QueryObjectType`:class:.


.. class:: Frame(locals, globals)

   Instances of this class implement the interface
   `xotl.ql.interfaces.Frame`:class: and the class itself complies with
   `xotl.ql.interface.FrameType`:class:.

   The `f_locals` and `f_globals` are immutable mapping views that support all
   the `collections.Mapping` interface.

   In order to support for the view concept to work we keep a references to
   the original `locals` and `globals`.

   .. rubric:: Additional attributes and methods:

   .. attribute:: auto_expand_subqueries

      When trying to get the name '.0' from either view, if the current value
      is a generator object obtained via a generator expression, we actually
      return the result of calling `get_query_object`:func: on the current
      value.

      You may suppress this behavior by setting this attribute to False.  The
      default is True.

      .. warning:: Notice this will use the default query object type and
         frame type.

      Example::

         >>> from xotl.ql.core import this, get_query_object
         >>> query = get_query_object(y for y in (x for x in this))

         >>> query.locals['.0']  # doctest: +ELLIPSIS
         <xotl.ql.core.QueryObject...>

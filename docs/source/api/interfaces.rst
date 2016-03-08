==================================================
 `xotl.ql.interfaces`:mod: -- The core interfaces
==================================================

.. automodule:: xotl.ql.interfaces

.. autoclass:: QueryObject
   :members: qst, locals, globals, get_name

.. autoclass:: QueryObjectType
   :members: __call__

.. autoclass:: Frame
   :members: f_locals, f_globals

.. autoclass:: FrameType
   :members: __call__

.. autoclass:: QueryTranslator
   :members: __call__

.. autoclass:: QueryExecutionPlan
   :members: query, __call__, __iter__

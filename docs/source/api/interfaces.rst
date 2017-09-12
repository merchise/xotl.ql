==================================================
 `xotl.ql.interfaces`:mod: -- The core interfaces
==================================================

.. automodule:: xotl.ql.interfaces

.. autointerface:: QueryObject
   :members: qst, locals, globals, get_value

.. autointerface:: QueryObjectType
   :members: frame_type, __call__

.. autointerface:: Frame
   :members: f_locals, f_globals

.. autointerface:: FrameType
   :members: __call__

.. autointerface:: QueryTranslator
   :members: __call__

.. autointerface:: QueryExecutionPlan
   :members: query, __call__, __iter__

.. autointerface:: QueryTranslatorExplainExtension
   :members: explain

.. autointerface:: QueryExecutionPlanExplainExtension
   :members: explain

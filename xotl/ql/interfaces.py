#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------
# Copyright (c) Merchise Autrement [~º/~] and Contributors
# All rights reserved.
#
# This is free software; you can do what the LICENCE file allows you to.
#

'''Interfaces that describe the major types used in the Query Language API,
and some internal interfaces as well.

Notice that we only aim for documentation of the types and not implementation.

We also explicitly divide the type of the objects from the type of object
constructors.  Given that types in Python are callable the type of object
constructors can be provided via the `__init__` method.

'''

import types
from xoutil.future import inspect


class MemberDescription:
    def __init__(self, val):
        self.val = val

    @property
    def name(self):
        return self.val.__name__

    @property
    def signature(self):
        if not isinstance(self.val, Attribute):
            positional = object()
            spec = inspect.getfullargspec(self.val)
            args = list(spec.args)
            if args[0] == 'self':
                args.pop(0)
            defaults = list(spec.defaults or [])
            if len(defaults) < len(args):
                defaults[0:0] = [positional] * (len(args) - len(defaults))

            return '(%s)' % ', '.join(
                '%s' % arg if val is positional else '%s=%s' % (arg, val)
                for arg, val in zip(args, defaults)
            )
        else:
            return None

    @property
    def doc(self):
        return self.val.__doc__


class InterfaceType(type):
    @property
    def members(self):
        return [attr for attr, val in self.__dict__.items()
                if isinstance(val, (Attribute, types.FunctionType))]

    def describe(self):
        return (
            (m.__name__, MemberDescription(m))
            for attr in self.members
            for m in (getattr(self, attr), )
        )

    def __instancecheck__(self, instance):
        attrs = self.members
        res = True
        while res and attrs:
            attr = attrs.pop()
            res = hasattr(instance, attr)
        return res
    __subclasscheck__ = __instancecheck__


class Interface(metaclass=InterfaceType):
    '''Define an interface.

    Interfaces support a weak 'instance' test definition::

      >>> class IStartswith(Interface):
      ...    def startswith():
      ...        pass

      >>> isinstance('', IStartswith)
      True

    '''


class Attribute:
    def __init__(self, name, doc):
        self.name = self.__name__ = name
        self.__doc__ = doc


class QueryObject(Interface):
    '''The required API-level interface for query objects.

    Query objects provide access to the QST for the query.

    '''
    qst = Attribute('qst', 'The Query Syntax Tree')

    locals = Attribute(
        'locals',
        'A MappingView for the locals in the query scope. '
        'See `get_value`:meth:'
    )

    globals = Attribute(
        'globals',
        'A MappingView for the globals in the query scope. '
        'See `get_value`:meth:'
    )

    def get_value(self, name, only_globals=False):
        '''Give the value for the `name`.

        Queries are defined in a scope where they could access any name
        (e.g. variables).  The translator may need to access the value of such
        names.

        Get name will prefer locals over globals unless `only_globals` is
        True.

        '''


class PartionableQueryObject(QueryObject):
    def limit_by(self, limit):
        '''Return a new query object limited by limit.

        If this query object already has a limit it will be ignore.

        '''

    def offset(self, offset):
        '''Return a new query object with a new offset.'''

    partition = Attribute(
        'partition',
        'A slice indicating how much to fetch '
        'from the data store.  The interpretation of this '
        'slice value should be consistent with that of '
        'Python own slice type.'
    )


class QueryExecutionPlan(Interface):
    '''Required API-level interface for a query execution plan.

    '''
    query = Attribute(
        'query',
        'The original query object this plan was built from.  Even if the '
        'translator was given a query expression directly, like in most of '
        'our examples, this must be a query object.'
    )

    def __call__(self, **kwargs):
        '''Execution plans are callable.

        Return an iterator.  The returned iterator must produce the objects
        retrieved from the query.  Though the plan itself is reusable and can
        be called several times, the iterator obtained from this method will
        be exhausted.

        Translators are required to properly document the optional keyword
        arguments.  Positional arguments are not allowed.  All arguments must
        be optional.

        '''

    def __iter__(self):
        '''Execution plans are iterable.

        This is exactly the same as calling the plan without any arguments:
        ``plan()``.

        '''
        return self()


class QueryTranslator(Interface):
    '''A query translator.

    .. note:: Since Python classes are callable, you may implement a
       translator/execution plan in a single class::

         >>> class ExecutionPlan:
         ...     def __init__(self, query, **kwargs):
         ...         pass
         ...
         ...     def __call__(self, **options):
         ...         pass
         ...
         ...     def __iter__(self):
         ...         return self()

       However this may hurt some extensions.  For instance, below we describe
       a couple of possible extensions for translators and plans which are not
       easily implemented in a single unit of code.

    '''
    def __call__(self, query, **kwargs):
        '''Return an execution plan for the given `query`.

        :param query: The query to be translated.  Translators must allow this
                       object to be either a `query expression` or a `query
                       object` that complies with the interface
                       `QueryObject`:class:.

        Translators are allowed to provide other keyword-only arguments.
        Translators' authors are encouraged to properly document those
        arguments.

        :return: The query execution plan.
        :rtype: `QueryExecutionPlan`:class:

        '''


class QueryTranslatorExplainExtension(QueryTranslator):
    '''This interface documents optional-methods for query translators that
    are deemed required to provide interactive access to the translator.

    '''

    def explain(self, query, **kwargs):
        '''Prints information about how the query might be translated/executed.

        The signature *should* allow the same arguments as the `__call__`
        method of translators.

        '''


class QueryExecutionPlanExplainExtension(QueryExecutionPlan):
    def explain(self):
        '''Prints information about this plan of execution.

        The details of the information are specific to the kind of plan.

        '''


class QueryDebugger(QueryTranslator):
    '''A translator with debugging capabilities.

    '''
    def debug(self, query, **kwargs):
        '''Enter a interactive session of debugging the provided query.

        '''


class QueryObjectType(Interface):
    '''A QueryObject factory.

    '''
    frame_type = Attribute(
        'frame_type',
        'An instance of `FrameType`:class: or the fully-qualified name of '
        'such an instance.'
    )

    def __call__(self, qst, frame, **kwargs):
        '''Return an instance of a `QueryObject`:class:.

        :param qst: The Query Syntax Tree.  It will become the attribute
               `QueryObject.qst`:attr:.

        :param frame: An instance of a `Frame`:class: object.  This should be
               used to provide the values of the attributes
               `QueryObject.locals`:attr: and `QueryObject.globals`:attr: and
               also to implement the method `QueryObject.get_value`:meth:.

        Different implementations of the `QueryObject` may required or support
        additional keyword arguments.  For instance, the type of a
        `PartionableQueryObject`:class: may allow for a `partition` argument.

        '''

    frame_type = Attribute(
        'frame_type',
        'Either a `FrameType`:class: object or the fully qualified name of '
        'such an object.  This object is used '
    )


class Frame(Interface):
    '''A object that represents a Python stack frame.

    This is an unavoidable requirement consequence of the `query
    expression`:term: being a generator object that may access names which are
    not known to the translator.

    The attributes f_locals and f_globals are required to be mappings (usually
    immutable) or mapping views that give access to the values of locals and
    globals of a stack frame.

    '''
    f_locals = Attribute(
        'f_locals',
        'A mapping of the locals of this frame.  Though not required '
        'this could be a mapping view provided it has the mapping '
        'interface.'
    )

    f_globals = Attribute(
        'f_globals',
        'A mapping of the globals of this frame.  Though not required '
        'this could be a mapping view provided it has the mapping '
        'interface.'
    )


class FrameType(Interface):
    '''A Frame factory.
    '''
    def __call__(self, locals, globals):
        '''Return a instance of a `Frame`:class: object.

        :param locals: A mapping that provide access to locals.
        :param globals: A mapping that provide access to globals.

        '''

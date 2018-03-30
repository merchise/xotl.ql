#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------
# Copyright (c) Merchise Autrement [~º/~] and Contributors
# All rights reserved.
#
# This is free software; you can do what the LICENCE file allows you to.
#

from xoutil.modules import modulemethod

from xotl.ql.core import normalize_query
from xotl.ql.interfaces import QueryObject

from .monads import mcompile, LazyCons, Map, Unit, Join, Empty


@modulemethod
def __call__(self, query, **kwargs):
    return self.NaivePythonExecutionPlan(query, **kwargs)


@modulemethod
def explain(self, query, **kwargs):
    '''Print information about how the query is processed.

    This function actually translates the query into a plan and explains the
    plan.

    .. seealso:: `NaivePythonExecutionPlan.explain`:method:

    '''
    self.NaivePythonExecutionPlan(query, **kwargs).explain()


class NaivePythonExecutionPlan:
    def __init__(self, query, map=None, join=None, zero=None, unit=None,
                 use_own_monads=False):
        # The map, join, zero, and unit are provided for tests.
        self.query = query = normalize_query(query)
        self.map = '__x_map_%s' % id(self) if not map else map
        self.join = '__x_join_%s' % id(self) if not join else join
        self.zero = '__x_zero_%s' % id(self) if not zero else zero
        self.unit = '__x_unit_%s' % id(self) if not unit else unit
        self.use_own_monads = use_own_monads
        self.plan = plan = mcompile(
            query.qst,
            map=self.map,
            join=self.join,
            zero=self.zero,
            unit=self.unit
        )
        self.compiled = compile(plan, '', 'eval')

    def explain(self):
        '''Prints information about how the query is going to be executed.

        This prints the `Query Syntax Tree`:term:, the Syntax Tree of the
        monad-based plan for executing the query, and the byte-code for the
        compile plan.

        The QST is transformed according to the algorithm described in
        [QLFunc]_.

        In the monadic plan the names of the Map, Join, Unit and Empty
        operators are 'randomized'.

        '''
        import dis
        print('\nOriginal query QST')
        print(str(self.query.qst))
        print('\nMonadic plan')
        print(str(self.plan))
        print('\nCompiled')
        dis.dis(self.compiled)

    @property
    def operators(self):
        if self.use_own_monads:
            return {
                self.map: Map,
                self.join: Join,
                self.unit: Unit,
                self.zero: Empty,
            }
        else:
            # In the following we use a 'mathematical' notation for variable
            # names: `f` stands for function, `l` stands for list (or
            # collection), `lls` stands for list of lists and `x` any item in
            # a list.
            __do_plan = self._do_plan
            return {
                # These functions must return iterators since the _mc uses
                # results from
                self.map: lambda f: lambda l: iter(f(x) for x in __do_plan(l)),
                self.join: lambda lls: iter(x for l in lls for x in l),
                self.unit: lambda x: iter([x]),
                self.zero: lambda: iter([]),
            }

    def _plan_dict_(self, other, modules=None, use_ignores=True):
        from xotl.ql.core import this

        def universe():
            return PythonObjectsCollection(
                modules,
                use_ignores=use_ignores,
                ascons=self.use_own_monads
            )

        return {
            name: (val if val is not this else universe())
            for name, val in other.items()
        }

    def __call__(self, modules=None, use_ignores=True):
        from xoutil.future.collections import ChainMap
        return eval(
            self.compiled,
            # Don't split the globals and locals... Why?
            #
            # When we parse the byte-code, opcodes like LOAD_NAME, LOAD_FAST,
            # LOAD_DEREF, and LOAD_LOCAL are all cast to a the same QST
            # `qst.Name(..., qst.Load())` where the local/global/cell
            # distinction is lost.
            #
            # The 'core.py' treats the name '.0' specially since they're most
            # likely subqueries.  But then, those subqueries carry their own
            # local/global and the loss of context can lead to bad guesses.
            #
            # This is evident in the the implementation of `thesefy`, where
            # the 'self' is confused with a global.
            #
            dict(ChainMap(
                self._plan_dict_(self.query.locals, modules, use_ignores),
                self._plan_dict_(self.query.globals, modules, use_ignores),
                self.operators
            ))
        )

    def _do_plan(self, what):
        if isinstance(what, QueryObject):
            return NaivePythonExecutionPlan(
                what,
                map=self.map,
                join=self.join,
                unit=self.unit,
                zero=self.zero
            )
        else:
            return what

    def __iter__(self):
        return self()


class _TestPlan(NaivePythonExecutionPlan):
    # A plan that fixes
    def __init__(self, query, **kwargs):
        super().__init__(
            query,
            map='Map',
            join='Join',
            zero='Empty',
            unit='Unit',
            **kwargs
        )


class PythonObjectsCollection:
    '''Represent the entire collection of Python objects.'''

    def __init__(self, modules=None, use_ignores=True, ascons=False):
        self.modules = modules
        self.use_ignores = use_ignores
        self.ascons = ascons

    @property
    def collection(self):
        modules = self.modules
        if modules:
            res = _iter_objects(accept=_filter_by_pkg(*modules),
                                use_ignores=self.use_ignores)
        else:
            res = _iter_objects(use_ignores=self.use_ignores)
        if self.ascons:
            try:
                head = next(res)
            except StopIteration:
                return Empty()
            return iter(LazyCons(head, list(res)))
        else:
            return res

    def __iter__(self):
        return self.collection


def _iter_objects(accept=None, use_ignores=False):
    '''Iterates over all objects currently in Python's VM memory for which
    ``accept(ob)`` returns True.

    '''
    import gc
    if use_ignores:
        filterby = lambda x: not defined(x, _avoid_modules) and (
            not accept or accept(x))
    else:
        filterby = accept
    return (ob for ob in gc.get_objects()
            if not isinstance(ob, type) and (not filterby or filterby(ob)))


def defined(who, modules):
    '''Checks if `who` (or its class) is defined in any of the given
    `modules`.

    The `modules` sequence may contains elements ending in ".*" to signify a
    package.

    '''
    if not isinstance(who, type):
        mod = type(who).__module__
    else:
        mod = who.__module__

    def check(target):
        if target.endswith('.*'):
            return mod.startswith(target[:-2])
        else:
            return mod == target
    return any(check(target) for target in modules)


def _iter_classes(accept=None, use_ignores=False):
    '''Iterates over all the classes currently in Python's VM memory
    for which `accept(cls)` returns True.

    If use_ignores is True classes and objects of types defined in xotl.ql's
    modules and builtins will be also ignored.

    '''
    import gc
    if use_ignores:
        if accept:
            def filterby(x):
                return not defined(x, _avoid_modules) and accept(x)
        else:
            def filterby(x):
                return not defined(x, _avoid_modules)
    else:
        filterby = accept
    return (ob for ob in gc.get_objects()
            if isinstance(ob, type) and (not filterby or filterby(ob)))


# Real signature is _filter_by_pkg(*pkg_names, negate=False)
def _filter_by_pkg(*pkg_names, **kwargs):
    '''Returns an `accept` filter for _iter_classes/_iter_objects that only
    accepts classes/objects defined in pkg_names.

    '''
    negate = kwargs.get('negate', False)

    def accept(cls):
        result = defined(cls, pkg_names)
        return result if not negate else not result
    return accept


# Modules whose objects are always "outside" this translator's view of the
# universe.
_avoid_modules = (
    'xotl.ql.*', 'xoutil.*', 'py.*', 'IPython.*',
    # The name of the builtins module is different in Pythons versions.
    type(1).__module__
)

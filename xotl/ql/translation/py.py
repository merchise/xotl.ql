#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# ---------------------------------------------------------------------
# xotl.ql.translation.py
# ---------------------------------------------------------------------
# Copyright (c) 2013-2016 Merchise Autrement and Contributors
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under
# the terms of the LICENCE attached in the distribution package.
#
# Created on 2013-04-03

from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)


class ExecPlan(object):
    def __init__(self, query):
        from ._monads import _mc
        self.query = query
        self.map = '__x_map_%s' % id(self)
        self.join = '__x_join_%s' % id(self)
        self.zero = '__x_zero_%s' % id(self)
        self.unit = '__x_unit_%s' % id(self)
        self.plan = plan = _mc(query.qst, map=self.map, join=self.join,
                               zero=self.zero, unit=self.unit)
        self.compiled = compile(plan, '', 'eval')

    def explain(self):
        import dis
        import ast
        print('\n\nOriginal query QST')
        print(ast.dump(self.query.qst))
        print('\n\nMonadic plan')
        print(ast.dump(self.plan))
        print('\n\nCompiled')
        dis.dis(self.compiled)

    def _plan_dict_(self, other, modules=None, use_ignores=True):
        from xotl.ql.core import this
        from xoutil.collections import ChainMap
        universe = lambda: iter(
            PythonObjectsCollection(modules, use_ignores=use_ignores)
        )
        return ChainMap(
            # In the following we use a 'mathematical' notation for variable
            # names: `f` stands for function, `l` stands for list (or
            # collection), `lls` stands for list of lists and `x` any item in
            # a list.
            {self.map: lambda f: lambda l: map(f, l),
             self.join: lambda lls: [x for l in lls for x in l],
             self.unit: lambda x: [x],
             self.zero: lambda: [], },
            # notice that for each instance of `this` a new universe needs to
            # be create.
            {name: val if val is not this else universe()
             for name, val in other.items()},
        )

    def __call__(self, modules=None, use_ignores=True):
        return eval(
            self.compiled,
            dict(self._plan_dict_(self.query.globals, modules, use_ignores)),
            self._plan_dict_(self.query.locals, modules, use_ignores)
        )


class PythonObjectsCollection(object):
    '''Represent the entire collection of Python objects.'''

    def __init__(self, modules=None, use_ignores=True):
        self.modules = modules
        self.use_ignores = use_ignores

    @property
    def collection(self):
        modules = self.modules
        if modules:
            res = _iter_objects(accept=_filter_by_pkg(*modules),
                                use_ignores=self.use_ignores)
        else:
            res = _iter_objects(use_ignores=self.use_ignores)
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
        filterby = lambda x: not defined(x, _avoid_modules) and (
            not accept or accept(x))
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

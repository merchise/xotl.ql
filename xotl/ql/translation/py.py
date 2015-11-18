#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# ---------------------------------------------------------------------
# xotl.ql.translation.py
# ---------------------------------------------------------------------
# Copyright (c) 2013-2015 Merchise Autrement and Contributors
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under
# the terms of the LICENCE attached in the distribution package.
#
# Created on 2013-04-03

from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)

# Modules whose objects are always "outside" this translator's view of the
# universe.
_avoid_modules = ('xotl.ql.*',
                  'xoutil.*',
                  'py.*',
                  'IPython.*',

                  # The name of the builtins module is different in Pythons
                  # versions.
                  type(1).__module__)


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


def get_term_vm_path(term):
    '''Gets the root and the "path" of a term in the VM.

    The root is actually the token to which this term is bound to.

    The path is a list of identifiers which are traversal steps from the
    root. For instance::

          these(child for parent in this
                if parent.children and parent.age > 33
                for child in parent.children
                if child.age < 5)

    The term `child.age` in the last filter is actually encoded by the names:
    parent, children, age; but since this term is bound to `parent.children`,
    only `age` is part of the path.

    '''
    pass


class _object(object):
    '''The type for objects build by ``new(object, ...)``.'''
    def __init__(self, **kwargs):
        self.__dict__ = kwargs.copy()


class ExecPlan(object):
    def __init__(self, query):
        from ._monads import _mc
        self.query = query
        qst = query.qst
        self.plan = plan = _mc(qst)
        self.compiled = compile(plan, '', 'eval')

    def __call__(self, modules=None, use_ignores=True):
        from ._monads import Min, Max, Sum, All, Any
        return eval(self.compiled, {
            'this': PythonObjectsCollection(modules, use_ignores=use_ignores),
            'all': All,
            'any': Any,
            'sum': Sum,
            'min': Min,
            'max': Max,
        })


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
        res = self.collection
        x = next(res)
        return iter(LightCons(x, res))

    def asiter(self):
        x, xs = self
        yield x
        for x in xs.asiter():
            yield x


class LightCons(object):
    def __init__(self, x, xs):
        self.x = x
        self.xs = xs

    def __iter__(self):
        from ._monads import Empty
        yield self.x
        xs = self.xs
        peek = next(xs, Empty())
        if isinstance(peek, Empty):
            yield peek
        else:
            yield LightCons(peek, xs)

    def asiter(self):
        x, xs = self
        while xs:
            yield x
            x, xs = xs
        yield x

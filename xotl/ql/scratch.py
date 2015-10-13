# -*- encoding: utf-8 -*-
# ---------------------------------------------------------------------
# scratch
# ---------------------------------------------------------------------
# Copyright (c) 2014, 2015 Merchise Autrement and Contributors
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the LICENCE attached (see LICENCE file) in the distribution
# package.
#
# Created on 2014-11-06

'''An scratch pad for ideas.

.. warning:: Nothing done in here is guarantee to remain in this package.

'''


from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)


from xoutil.eight.meta import metaclass


_unary_operators = {
    '__pos__': '+A',
    '__neg__': '-A',
    '__abs__': '|A|',
    '__invert__': '~A',
}

_binary_operators = {
    '__add__': 'A+B',
    '__sub__': 'A-B',
    '__mul__': 'A*B',
    '__div__': 'A/B',
    '__truediv__': 'A/B',
    '__floordiv__': 'A//B',
    '__pow__': 'A**B',
    '__mod__': 'A%B',
    '__divmod__': 'A/%B',
    '__lshift__': 'A<<B',
    '__rshift__': 'A>>B',
    '__and__': 'A&B',
    '__xor__': 'A^B',
    '__or__': 'A|B'
}

_rbinary_operators = {
    '__r{}__'.format(attr.strip('_')): val
    for attr, val in _binary_operators.items()
}

# Non reversible
_binary_operators.update({
    '__getitem__': 'A[B]',
})


def _expression_type(name, bases, attrs):
    for attr, val in _binary_operators.items():
        operator = (lambda v: lambda self, other: res((v, self, other)))(val)
        operator.__name__ = attr
        attrs[attr] = operator
    for attr, val in _rbinary_operators.items():
        operator = (lambda v: lambda self, other: res((v, other, self)))(val)
        operator.__name__ = attr
        attrs[attr] = operator
    for attr, val in _unary_operators.items():
        operator = (lambda v: lambda self: res((v, self)))(val)
        operator.__name__ = attr
        attrs[attr] = operator
    res = type(name, bases, attrs)
    return res


class Expression(object):
    pass


class Expr(metaclass(_expression_type), Expression):
    def __init__(self, val=None):
        self.val = val

    def __repr__(self):
        return '<expr: {0!r}>'.format(self.val)

    def __call__(self, *args, **kwargs):
        return Expr(('F(...)', self, args, kwargs))


def Var(name):
    return Expr(('var', name))


def Name(name):
    return Expr(('token', name))


def detect_names(expr, debug=False):
    trap = trapper()
    res = eval(expr, trap)
    if not isinstance(res, Expression):
        raise ValueError('Invalid expression')
    if not debug:
        return trap.keys()
    else:
        return trap.keys(), res


class trapper(dict):
    def __getitem__(self, key):
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            if not key.startswith('__'):
                self[key] = res = Name(key)
                return res
            else:
                raise

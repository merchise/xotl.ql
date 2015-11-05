#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# ---------------------------------------------------------------------
# qst
# ---------------------------------------------------------------------
# Copyright (c) 2015 Merchise Autrement and Contributors
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the LICENCE attached (see LICENCE file) in the distribution
# package.
#
# Created on 2015-11-05

'''The Query Syxtax Tree.

'''

from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)


from xoutil.types import new_class
import ast as pyast

# For each AST class in the Python ast module we build a new one here that
# supports equality comparison::
#
#    qst.Name('a', qst.Load()) == qst.Name('b', qst.Load())
#


from xoutil.objects import validate_attrs
if getattr(validate_attrs, '_positive_testing', None):
    # If `validate_attrs` uses the old implementation of negative testing, it
    # cannot be used for implementing __eq__.
    def _eq_asts(self, other):
        from xoutil.objects import validate_attrs as validate
        return validate(self, other, force_equals=self._fields)
else:
    def _eq_asts(self, other):
        from xoutil.objects import smart_getter
        from operator import eq
        res = True
        get_from_source = smart_getter(self)
        get_from_target = smart_getter(other)
        i = 0
        attrs = self._fields
        while res and (i < len(attrs)):
            attr = attrs[i]
            if eq(get_from_source(attr), get_from_target(attr)):
                i += 1
            else:
                res = False
        return res


class PyASTNodeType(type(pyast.AST)):
    def __instancecheck__(self, instance):
        pass


class PyASTNode(object):
    __eq__ = _eq_asts

    @classmethod
    def from_pyast(cls, node):
        '''Convert an `ast.AST`:py:class: node into the equivalent qst node.'''
        def _convert(value):
            if value:
                type_ = globals().get(type(value).__name__, None)
                if type_:
                    value = type_.from_pyast(value)
            return value

        assert cls.__name__ == type(node).__name__
        res = cls()
        for attr in node._attributes:
            setattr(res, attr, getattr(node, attr, None))
        for field in node._fields:
            value = getattr(node, field, None)
            if isinstance(value, list):
                value = [_convert(val) for val in value]
            elif isinstance(value, tuple):
                value = tuple(_convert(val) for val in value)
            else:
                value = _convert(value)
            setattr(res, field, value)
        return res

del validate_attrs, _eq_asts

__all__ = []
_nodes = [pyast.Expression, pyast.expr, pyast.boolop, pyast.unaryop, pyast.keyword,
          pyast.slice, pyast.operator, pyast.cmpop, pyast.comprehension,
          pyast.arguments, pyast.expr_context]
_current = 0

while _current < len(_nodes):
    _node = _nodes[_current]
    _more = _node.__subclasses__()  # Don't place this after the new class.

    globals()['_PyAst_%s' % _node.__name__] = _node
    # Has a constructor create the class for comparing
    globals()[_node.__name__] = new_class(_node.__name__,
                                          bases=(PyASTNode, _node))
    __all__.append(_node.__name__)

    if _more:
        _nodes.extend(_more)
    _current += 1


def parse(source, filename='<unknown>', mode='eval'):
    assert mode == 'eval'
    res = pyast.parse(source, filename, mode)
    return Expression.from_pyast(res)    # noqa

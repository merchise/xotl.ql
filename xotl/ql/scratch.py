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

import ast


def detect_names(expr, debug=False):
    '''Detect the (variable) names that are used free in the 'expr'.

    Examples::

        >>> detect_names('all(x for x in this for y in those if p(y)'
        ...              '      for z in y)')
        {'this', 'those', 'p', 'all'}

        >>> detect_names('(lambda x: lambda y: x + y)(x)')

    '''
    tree = ast.parse(expr, '', 'eval')
    detector = NameDetectorVisitor()
    detector.visit(tree.body)  # Go directly to the body
    return detector.freevars


class NameDetectorVisitor(ast.NodeVisitor):
    def _with_new_frame(f=None):
        def method(self, node):
            self.push_stack_frame()
            if f is None:
                self.generic_visit(node)
            else:
                f(self, node)
            self.pop_stack_frame()
        return method

    def __init__(self):
        self.frame = frame = set()
        self.stack = [frame]
        self.freevars = set()

    def push_stack_frame(self):
        self.frame = frame = set()
        self.stack.append(frame)

    def pop_stack_frame(self):
        return self.stack.pop(-1)

    def visit_Name(self, node):
        if isinstance(node.ctx, (ast.Store, ast.Param)):
            self.bind_variable(node.id)
        elif node.id not in self.bound_variables:
            self.report_free_variable(node.id)
        else:
            self.report_bound_variable(node.id)

    @property
    def bound_variables(self):
        return {name for frame in self.stack for name in frame}

    def bind_variable(self, name):
        self.frame.add(name)

    def report_free_variable(self, name):
        self.freevars.add(name)

    def report_bound_variable(self, name):
        pass

    visit_Lambda = _with_new_frame()

    @_with_new_frame
    def visit_GeneratorExp(self, node):
        # Invert the order of fields so that bound variables are properly
        # detected in the current frame.
        for comp in node.generators:
            self.visit(comp)
        self.visit(node.elt)

    visit_SetComp = visit_ListComp = visit_GeneratorExp

    @_with_new_frame
    def visit_DictComp(self, node):
        for comp in node.comprehesions:
            self.visit(comp)
        self.visit(node.key)
        self.visit(node.value)

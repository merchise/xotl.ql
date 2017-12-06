#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------
# Copyright (c) Merchise Autrement [~º/~] and Contributors
# All rights reserved.
#
# This is free software; you can do what the LICENCE file allows you to.
#

'''Tools to work with AST and QST.

'''


from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)

import ast
import sys

_py2 = (2, 0) <= sys.version_info < (3, 0)


try:
    from xoutil.objects import import_object   # TODO: migrate
except ImportError:
    def import_object(name, package=None,
                      sep='.', default=None, **kwargs):
        """Get symbol by qualified name.

        The name should be the full dot-separated path to the class::

            modulename.ClassName

        Example::

            xotl.ql.core.QueryObject
                        ^- class name

        or using ':' to separate module and symbol::

            xotl.ql.core:QueryObject

        Examples:

            >>> import_object('xotl.ql.core.QueryObject')
            <class 'xotl.ql.core.QueryObject'>

            # Does not try to look up non-string names.
            >>> from xotl.ql.core import QueryObject
            >>> import_object(QueryObject) is QueryObject
            True

        """
        import importlib
        from xoutil.eight import string_types
        imp = importlib.import_module
        if not isinstance(name, string_types):
            return name                                 # already a class
        sep = ':' if ':' in name else sep
        module_name, _, cls_name = name.rpartition(sep)
        if not module_name:
            cls_name, module_name = None, package if package else cls_name
        try:
            module = imp(module_name, package=package, **kwargs)
            return getattr(module, cls_name) if cls_name else module
        except (ImportError, AttributeError):
            if default is None:
                raise
        return default


def detect_names(expr):
    '''Detect the (variable) names that are used free in the 'expr'.

    Examples::

        >>> detect_names('all(x for x in this for y in those if p(y)'
        ...              '      for z in y)')
        {'this', 'those', 'p', 'all'}

        >>> detect_names('(lambda x: lambda p, y=p(x): x + y)(x)')
        {'x', 'p'}

    '''
    if not isinstance(expr, ast.AST):
        tree = ast.parse(expr, '', 'eval')
    else:
        tree = expr
    detector = NameDetectorVisitor()
    detector.visit(tree)
    return detector.freevars


# Helper for NameDetectorVisitor to create the visitor methods that push and
# pop a new stack frame.
def _with_new_frame(f=None):
    def method(self, node):
        self.push_stack_frame()
        if f is None:
            self.generic_visit(node)
        else:
            f(self, node)
        self.pop_stack_frame()
    return method


class NameDetectorVisitor(ast.NodeVisitor):
    '''Traverse the AST and collects names.

    The visitor calls the `report_free_variable`:meth: for each occurrence of
    a free variable, and calls the `report_bound_variable`:meth: for each
    occurrence of a bound variable.

    Sub-classes may override the `report_free_variable`:meth: and
    `report_bound_variable`:meth:.  The default is to collect free variables
    in the `freevars`:attr: set.

    Notice that a variable may appear bound and free in the same expression::

        (lambda x: x)(x)

    In that expression the first occurrence of `x` establish it a bound
    variable for the body of the lambda, the second occurrence of `x` is
    bound, and the third occurrence is free since it's not affected by the
    binding of the lambda.

    The visitor will report 'x' as both free and bound.


    '''
    def __init__(self):
        self.frame = frame = set()
        self.stack = [frame]
        self.freevars = set()

    def report_free_variable(self, name):
        self.freevars.add(name)

    def report_bound_variable(self, name):
        pass

    def push_stack_frame(self, frame=None):
        if not frame:
            frame = set()
        self.frame = frame
        self.stack.append(frame)

    def pop_stack_frame(self):
        result = self.stack.pop(-1)
        self.frame = self.stack[-1]
        return result

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

    visit_FunctionDef = visit_ClassDef = visit_Lambda = _with_new_frame()

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

    def visit_arguments(self, node):
        # Defaults should be evaluated in the context of the outer frame, not
        # the current function definition.  So we temporarily pop the frame,
        # visit the defaults, and the push the frame back before proceeding.
        _frame = self.pop_stack_frame()
        for default in node.defaults:
            self.visit(default)
        for default in getattr(node, 'kw_defaults', []):   # Python 3
            self.visit(default)
        self.push_stack_frame(_frame)
        # In Python 2 vararg and kwarg are identifiers not AST nodes, so the
        # 'visit' method for them is actually the bind_variable
        visit = self.bind_variable if _py2 else self.visit
        if node.vararg:
            visit(node.vararg)
        if node.kwarg:
            visit(node.kwargs)
        for arg in node.args:
            self.visit(arg)
        for arg in getattr(node, 'kwonlyargs', []):
            self.visit(arg)

    def visit_arg(self, node):
        self.bind_variable(node.arg)


del _with_new_frame

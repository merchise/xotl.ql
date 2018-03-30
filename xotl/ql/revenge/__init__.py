#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------
# Copyright (c) Merchise Autrement [~º/~] and Contributors
# All rights reserved.
#

# This is a fork of the uncompyle2 package.  It's been modified to better
# suite our coding standards and aim.
#
# The original copyright notice is kept in the file 'LICENCE.txt'.
#
# The name 'revenge' stands for "REVerse ENGineering using an Earley parser"
# ;)
#
#

import types
from xoutil.objects import memoized_property

from . import scanners, walkers
from .scanners import getscanner   # noqa:  exported
from .parsers import ParserError


class Uncompyled:
    '''A query object which is built from byte-code.
    '''
    def __init__(self, obj, version=None, get_current_thread=None,
                 islambda=False, hasnone=False):
        code = self._extract_code(obj)
        self.code = code
        if get_current_thread:
            scanner = scanners.getscanner(version, get_current_thread)
        else:
            # NON THREAD SAFE and NOT ISOLATED
            scanner = scanners.getscanner(version, lambda: 0)
        self.walker = walkers.QstBuilder(scanner)
        tokens, customizations = scanner.disassemble(code)
        self.islambda = islambda
        self.hasnone = hasnone or ('None' in code.co_names)
        self._tokens = tokens
        self._customizations = customizations

    def dis(self):
        # shortcut to print the code with dis
        import dis
        dis.dis(self.code)

    @property
    def tokens(self):
        return list(self._tokens)

    @property
    def customizations(self):
        return dict(self._customizations)

    @memoized_property
    def ast(self):
        tokens = self.tokens
        customizations = self.customizations
        try:
            ast = self.walker.build_ast(
                tokens, customizations,
                islambda=self.islambda,
                hasnone=self.hasnone
            )
        except ParserError as error:
            # So the debugger print the locals
            error.tokens = tokens
            raise error
        # Go down in the AST until the root has more than one children.
        while ast and len(ast) == 1:
            ast = ast[0]
        self._ast = ast
        return ast

    @property
    def qst(self):
        from .qst import ensure_compilable
        builder = self.walker
        builder.preorder(self.ast)
        return ensure_compilable(builder.stop())

    @property
    def safe_qst(self):
        try:
            return self.qst
        except Exception:
            return None

    @property
    def safe_ast(self):
        try:
            return self.ast
        except Exception:
            return None

    @classmethod
    def _extract_code(cls, obj):
        if isinstance(obj, types.CodeType):
            return obj
        elif isinstance(obj, types.GeneratorType):
            return obj.gi_code
        elif isinstance(obj, types.FunctionType):
            # We regard the closure-provided values as a kind of locals
            # variable
            return obj.__code__
        else:
            raise TypeError('Invalid code object')

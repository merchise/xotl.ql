# -*- encoding: utf-8 -*-
# ---------------------------------------------------------------------
# xotl.ql.revenge
# ---------------------------------------------------------------------
# Copyright (c) 2014, 2015 Merchise Autrement and Contributors
# All rights reserved.
#

# This is a fork of the uncompyle2 package.  It's being modified to better
# suite our coding standards and aim.  The original copyright notice is kept
# below.
#
# The name 'revenge' stands for "REVerse ENGineering using an Earley parser"
# ;)
#

#  Copyright (c) 1999 John Aycock
#  Copyright (c) 2000 by hartmut Goebel <h.goebel@crazy-compilers.com>
#
#  Permission is hereby granted, free of charge, to any person obtaining
#  a copy of this software and associated documentation files (the
#  "Software"), to deal in the Software without restriction, including
#  without limitation the rights to use, copy, modify, merge, publish,
#  distribute, sublicense, and/or sell copies of the Software, and to
#  permit persons to whom the Software is furnished to do so, subject to
#  the following conditions:
#
#  The above copyright notice and this permission notice shall be
#  included in all copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
#  EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
#  MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
#  IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
#  CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
#  TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
#  SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# See the file 'CHANGES' for a list of changes
#
# NB. This is not a masterpiece of software, but became more like a hack.
#     Probably a complete rewrite would be sensefull. hG/2000-12-27
#

from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)

import types
from . import scanners, walkers


class Uncompyled(object):   # TODO:  Find better name
    def __init__(self, obj, version=None):
        import io
        if not version:
            import sys
            version = sys.version.split(' ')[0]
        code = self._extract_code(obj)
        scanner = scanners.getscanner(version)
        self.walker = walker = walkers.Walker(scanner)
        tokens, customizations = scanner.disassemble(code)
        self.customizations = customizations
        ast = walker.build_ast(tokens, customizations)
        # Go down in the AST until the root has more than one children.
        while ast and len(ast) == 1:
            ast = ast[0]
        self.ast = ast

    @property
    def expression(self):
        import ipdb; ipdb.set_trace()

        self.walker.traverse(self.ast)
        pass

    @staticmethod
    def _extract_code(obj):
        import types
        if isinstance(obj, types.CodeType):
            return obj
        elif isinstance(obj, types.GeneratorType):
            return obj.gi_code
        elif isinstance(obj, types.FunctionType):
            from xoutil.objects import get_first_of
            return get_first_of(obj, 'func_code', '__code__')
        else:
            raise TypeError('Invalid code object')


def uncompyle(co, version=None):
    """Disassemble a given code block `co`.

    Return the `AST <xotl.ql.revenge.parsers.AST>`:class: (this is actually a
    low-level AST that we will call Concrete Syntax Tree, though that's not
    actually true).

    """
    import sys
    assert isinstance(co, types.CodeType)
    if not version:
        version = sys.version.split(' ')[0]
    scanner = scanners.getscanner(version)
    tokens, customizations = scanner.disassemble(co)
    #  Build AST from disassembly.
    walker = walkers.Walker(scanner)
    ast = walker.build_ast(tokens, customizations)
    del tokens  # save memory
    # convert leading '__doc__ = "..." into doc string
    assert ast.type == 'stmts'
    try:
        if ast[0][0] == walkers.ASSIGN_DOC_STRING(co.co_consts[0]):
            del ast[0]
        if ast[-1] == walkers.RETURN_NONE:
            ast.pop()
            # todo: if empty, add 'pass'
    except (IndexError, TypeError):
        pass
    return ast, customizations, walker

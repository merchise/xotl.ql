# -*- encoding: utf-8 -*-
#----------------------------------------------------------------------
# xotl.ql.revenge
#----------------------------------------------------------------------
# Copyright (c) 2014 Merchise Autrement and Contributors
# All rights reserved.
#

# This is fork of the uncompyle2 package.  It's being modified to better suite
# our coding standards and aim.  The original copyright notice is kept below.
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

import sys
import types


from . import scanners, walkers


def uncompyle(version, co, out=None, showasm=0, showast=0, deob=0):
    """
    diassembles a given code block 'co'
    """
    assert isinstance(co, types.CodeType)

    # store final output stream for case of error
    __real_out = out or sys.stdout
    if co.co_filename:
        print('#Embedded file name: %s' % co.co_filename, file=__real_out)
    scanner = scanners.getscanner(version)
    scanner.setShowAsm(showasm, out)
    tokens, customize = scanner.disassemble(co, deob=deob)

    #  Build AST from disassembly.
    walker = walkers.Walker(out, scanner, showast=showast)
    try:
        ast = walker.build_ast(tokens, customize)
    except walkers.ParserError as e:  # parser failed, dump disassembly
        print(e, file=__real_out)
        raise

    del tokens  # save memory

    # convert leading '__doc__ = "..." into doc string
    assert ast == 'stmts'
    try:
        if ast[0][0] == walkers.ASSIGN_DOC_STRING(co.co_consts[0]):
            walker.print_docstring('', co.co_consts[0])
            del ast[0]
        if ast[-1] == walkers.RETURN_NONE:
            ast.pop()  # remove last node
            #todo: if empty, add 'pass'
    except:
        pass
    walker.mod_globs = walkers.find_globals(ast, set())
    walker.gen_source(ast, customize)
    for g in walker.mod_globs:
        walker.write('global %s ## Warning: Unused global\n' % g)
    if walker.pending_newlines:
        print(file=__real_out)
    if walker.ERROR:
        raise walker.ERROR

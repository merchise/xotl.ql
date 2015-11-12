#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# ---------------------------------------------------------------------
# test_revenge
# ---------------------------------------------------------------------
# Copyright (c) 2015 Merchise Autrement and Contributors
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the LICENCE attached (see LICENCE file) in the distribution
# package.
#
# Created on 2015-10-25

from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)

import sys
_py3 = sys.version_info >= (3, 0)
del sys


def test_scanner_normalization():
    from xotl.ql.revenge.scanners import InstructionSetBuilder
    from xotl.ql.revenge.scanners import without_nops

    # The PyPy byte code for `a if b else c`:
    builder = InstructionSetBuilder()
    with builder() as Instruction:
        Instruction(opname='LOAD_NAME',
                    arg=0, argval='x', argrepr='x',
                    starts_line=1),
        Instruction(opname='POP_JUMP_IF_FALSE',
                    arg=12, argval=12, argrepr='',
                    starts_line=None),
        Instruction(opname='LOAD_NAME', arg=1,
                    argval='a', argrepr='a',
                    starts_line=None),
        # Replace the JUMP_FORWARD
        # Instruction(opname='JUMP_FORWARD', opcode=JUMP_FORWARD,
        #             arg=3, argval=15, argrepr='to 15', offset=9,
        #             starts_line=None, is_jump_target=False),
        Instruction(opname='RETURN_VALUE', arg=None,
                    argval=None, argrepr='',
                    starts_line=None),
        Instruction(opname='NOP', arg=None,
                    argval=None, argrepr='',
                    starts_line=None),
        Instruction(opname='NOP', arg=None,
                    argval=None, argrepr='',
                    starts_line=None),
        # End of replacement
        Instruction(opname='LOAD_NAME',
                    arg=2, argval='y', argrepr='y',
                    starts_line=None),
        Instruction(opname='RETURN_VALUE',
                    arg=None, argval=None, argrepr='',
                    starts_line=None)
    modified_pypy_program = list(builder)

    builder = InstructionSetBuilder()
    with builder() as Instruction:
        Instruction(opname='LOAD_NAME', arg=0,
                    argval='x', argrepr='x',
                    starts_line=1),
        Instruction(opname='POP_JUMP_IF_FALSE',
                    arg=10, argval=10, argrepr='',
                    starts_line=None),
        Instruction(opname='LOAD_NAME', arg=1,
                    argval='a', argrepr='a', offset=6,
                    starts_line=None),
        Instruction(opname='RETURN_VALUE',
                    arg=None, argval=None, argrepr='',
                    starts_line=None),
        Instruction(opname='LOAD_NAME', arg=2,
                    argval='y', argrepr='y',
                    starts_line=None),
        Instruction(opname='RETURN_VALUE', arg=None,
                    argval=None, argrepr='', starts_line=None)
    expected = list(builder)
    res = list(without_nops(modified_pypy_program))
    assert res == expected


def test_pypy_normalization():
    from xotl.ql.revenge.scanners import Instruction, LOAD_NAME
    from xotl.ql.revenge.scanners import POP_JUMP_IF_FALSE, POP_JUMP_IF_TRUE
    from xotl.ql.revenge.scanners import RETURN_VALUE, JUMP_FORWARD
    from xotl.ql.revenge.scanners import JUMP_ABSOLUTE, NOP
    from xotl.ql.revenge.scanners import normalize_pypy_conditional

    # The PyPy byte code for `a if b else c`:
    pypy_program = [
        Instruction(opname='LOAD_NAME', opcode=LOAD_NAME,
                    arg=0, argval='x', argrepr='x',
                    offset=0, starts_line=1, is_jump_target=False),
        Instruction(opname='POP_JUMP_IF_FALSE', opcode=POP_JUMP_IF_FALSE,
                    arg=12, argval=12, argrepr='', offset=3,
                    starts_line=None, is_jump_target=False),
        Instruction(opname='LOAD_NAME', opcode=LOAD_NAME, arg=1,
                    argval='a', argrepr='a', offset=6,
                    starts_line=None, is_jump_target=False),
        Instruction(opname='JUMP_FORWARD', opcode=JUMP_FORWARD,
                    arg=3, argval=15, argrepr='to 15', offset=9,
                    starts_line=None, is_jump_target=False),

        Instruction(opname='LOAD_NAME', opcode=LOAD_NAME,
                    arg=2, argval='y', argrepr='y', offset=12,
                    starts_line=None, is_jump_target=True),
        Instruction(opname='RETURN_VALUE', opcode=RETURN_VALUE,
                    arg=None, argval=None, argrepr='',
                    offset=15, starts_line=None, is_jump_target=True)
    ]

    modified_pypy_program = [
        Instruction(opname='LOAD_NAME', opcode=LOAD_NAME,
                    arg=0, argval='x', argrepr='x',
                    offset=0, starts_line=1, is_jump_target=False),
        Instruction(opname='POP_JUMP_IF_FALSE', opcode=POP_JUMP_IF_FALSE,
                    arg=12, argval=12, argrepr='', offset=3,
                    starts_line=None, is_jump_target=False),
        Instruction(opname='LOAD_NAME', opcode=LOAD_NAME, arg=1,
                    argval='a', argrepr='a', offset=6,
                    starts_line=None, is_jump_target=False),

        Instruction(opname='RETURN_VALUE', opcode=RETURN_VALUE, arg=None,
                    argval=None, argrepr='', offset=9,
                    starts_line=None, is_jump_target=False),
        Instruction(opname='NOP', opcode=NOP, arg=None,
                    argval=None, argrepr='', offset=10,
                    starts_line=None, is_jump_target=False),
        Instruction(opname='NOP', opcode=NOP, arg=None,
                    argval=None, argrepr='', offset=11,
                    starts_line=None, is_jump_target=False),

        Instruction(opname='LOAD_NAME', opcode=LOAD_NAME,
                    arg=2, argval='y', argrepr='y', offset=12,
                    starts_line=None, is_jump_target=True),
        Instruction(opname='RETURN_VALUE', opcode=RETURN_VALUE,
                    arg=None, argval=None, argrepr='',
                    offset=15, starts_line=None, is_jump_target=True)
    ]

    res = list(normalize_pypy_conditional(pypy_program))
    assert modified_pypy_program == res

    # Same program with JUMP_ABSOLUTE
    pypy_program = [
        Instruction(opname='LOAD_NAME', opcode=LOAD_NAME,
                    arg=0, argval='x', argrepr='x',
                    offset=0, starts_line=1, is_jump_target=False),
        Instruction(opname='POP_JUMP_IF_FALSE', opcode=POP_JUMP_IF_FALSE,
                    arg=12, argval=12, argrepr='', offset=3,
                    starts_line=None, is_jump_target=False),
        Instruction(opname='LOAD_NAME', opcode=LOAD_NAME, arg=1,
                    argval='a', argrepr='a', offset=6,
                    starts_line=None, is_jump_target=False),
        Instruction(opname='JUMP_ABSOLUTE', opcode=JUMP_ABSOLUTE,
                    arg=15, argval=15, argrepr='to 15', offset=9,
                    starts_line=None, is_jump_target=False),

        Instruction(opname='LOAD_NAME', opcode=LOAD_NAME,
                    arg=2, argval='y', argrepr='y', offset=12,
                    starts_line=None, is_jump_target=True),
        Instruction(opname='RETURN_VALUE', opcode=RETURN_VALUE,
                    arg=None, argval=None, argrepr='',
                    offset=15, starts_line=None, is_jump_target=True)
    ]

    res = list(normalize_pypy_conditional(pypy_program))
    assert modified_pypy_program == res

    # ``a if not b else c``
    pypy_program = [
        Instruction(opname='LOAD_NAME', opcode=LOAD_NAME,
                    arg=0, argval='b', argrepr='b',
                    offset=0, starts_line=1, is_jump_target=False),
        Instruction(opname='POP_JUMP_IF_TRUE', opcode=POP_JUMP_IF_TRUE,
                    arg=12, argval=12, argrepr='',
                    offset=3, starts_line=None, is_jump_target=False),
        Instruction(opname='LOAD_NAME', opcode=LOAD_NAME,
                    arg=1, argval='a', argrepr='a',
                    offset=6, starts_line=None, is_jump_target=False),
        Instruction(opname='JUMP_FORWARD', opcode=JUMP_FORWARD,
                    arg=3, argval=15, argrepr='to 15',
                    offset=9, starts_line=None, is_jump_target=False),
        Instruction(opname='LOAD_NAME', opcode=LOAD_NAME,
                    arg=2, argval='c', argrepr='c',
                    offset=12, starts_line=None, is_jump_target=True),
        Instruction(opname='RETURN_VALUE', opcode=RETURN_VALUE,
                    arg=None, argval=None, argrepr='',
                    offset=15, starts_line=None, is_jump_target=True)
    ]

    modified_pypy_program = [
        Instruction(opname='LOAD_NAME', opcode=LOAD_NAME,
                    arg=0, argval='b', argrepr='b',
                    offset=0, starts_line=1, is_jump_target=False),
        Instruction(opname='POP_JUMP_IF_TRUE', opcode=POP_JUMP_IF_TRUE,
                    arg=12, argval=12, argrepr='', offset=3,
                    starts_line=None, is_jump_target=False),
        Instruction(opname='LOAD_NAME', opcode=LOAD_NAME, arg=1,
                    argval='a', argrepr='a', offset=6,
                    starts_line=None, is_jump_target=False),

        Instruction(opname='RETURN_VALUE', opcode=RETURN_VALUE, arg=None,
                    argval=None, argrepr='', offset=9,
                    starts_line=None, is_jump_target=False),
        Instruction(opname='NOP', opcode=NOP, arg=None,
                    argval=None, argrepr='', offset=10,
                    starts_line=None, is_jump_target=False),
        Instruction(opname='NOP', opcode=NOP, arg=None,
                    argval=None, argrepr='', offset=11,
                    starts_line=None, is_jump_target=False),

        Instruction(opname='LOAD_NAME', opcode=LOAD_NAME,
                    arg=2, argval='c', argrepr='c', offset=12,
                    starts_line=None, is_jump_target=True),
        Instruction(opname='RETURN_VALUE', opcode=RETURN_VALUE,
                    arg=None, argval=None, argrepr='',
                    offset=15, starts_line=None, is_jump_target=True)
    ]

    res = list(normalize_pypy_conditional(pypy_program))
    assert modified_pypy_program == res


def test_real_pypy_normalization():
    from xotl.ql.revenge.scanners import InstructionSetBuilder, label
    from xotl.ql.revenge.scanners import getscanner

    # The PyPy byte code for `a if x else y`:
    builder = InstructionSetBuilder()
    with builder() as Instruction:
        Instruction(opname='LOAD_NAME',
                    arg=0, argval='x', argrepr='x',
                    starts_line=1, is_jump_target=False),
        Instruction(opname='POP_JUMP_IF_FALSE',
                    arg=label('else y'), starts_line=None)
        Instruction(opname='LOAD_NAME', arg=1,
                    argval='a', argrepr='a', starts_line=None)
        Instruction(opname='RETURN_VALUE',
                    arg=None, argval=None, argrepr='', starts_line=None)
        Instruction(label='else y',
                    opname='LOAD_NAME',
                    arg=2, argval='y', argrepr='y', starts_line=None),
        Instruction(opname='RETURN_VALUE',
                    arg=None, argval=None, argrepr='',
                    starts_line=None)
    expected_program = list(builder)
    scanner = getscanner()
    tokens, customize = scanner.disassemble(compile('a if x else y', '', 'eval'))
    instructions = [token.instruction for token in tokens if token.instruction]
    assert instructions == expected_program


# We're only testing we can build an AST from the byte-code.  This AST
# extracted from the byte-code directly and not the one we'll provide to
# translators.  The idea is to stabilize the parser from byte-code to this IST
# (Intermediate Syntax Tree).
#
# We'll extend the tests to actually match our target AST.


def test_basic_expressions():
    expressions = [
        ('a + b', None),
        ('lambda x, y=1, *args, **kw: x + y', None),
        ('(lambda x: x)(y)', None),
        ('c(a)', None),
        ('a & b | c ^ d', None),
        ('a << b >> c', None),
        ('a + b * (d + c)', None),
        ('a in b', None),
        ('a.attr.b[2:3]', None),
        ('a[1] + list(b)', None),
        ('{a: b,\n c: d}', None),
    ]
    _do_test(expressions)


def test_conditional_expressions():
    expressions = [
        # expr, expected source if different
        ('a if x else y', None),
        ('a and (b or c)', None),
        ('a and b or c', None),
        ('(a if x else y) if (b if z else c) else (d if o else p)', None),
        ('(a if x else y) if (b if z else c) else (d if not o else p)', None),
        ('(a if x else y) if not (b if not z else c) else (d if o else p)', None),
        ('(a if not x else y) if not (b if not z else c) else (d if not o else p)', None),
        ('c(a if x else y)', None),
        ('lambda : (a if x else y)', None),
        ('(lambda: x) if x else (lambda y: y)(y)', None),
    ]
    _do_test(expressions)


def test_conditional_a_la_pypy():
    # >>> dis.dis(compile('x and a or y', '', 'eval'))
    #   1           0 LOAD_NAME                0 (x)
    #               3 JUMP_IF_FALSE_OR_POP     9
    #               6 LOAD_NAME                1 (a)
    #         >>    9 JUMP_IF_TRUE_OR_POP     15
    #              12 LOAD_NAME                2 (y)
    #         >>   15 RETURN_VALUE
    import types
    from xotl.ql.revenge import Uncompyled
    from xotl.ql.revenge.scanners import InstructionSetBuilder, label
    builder = InstructionSetBuilder()
    with builder() as Instruction:
        Instruction(opname='LOAD_NAME', arg=0, argval='x', starts_line=1)
        Instruction(opname='JUMP_IF_FALSE_OR_POP', arg=label('else'))
        Instruction(opname='LOAD_NAME', arg=1, argval='a')
        Instruction(label='else',
                    opname='JUMP_IF_TRUE_OR_POP', arg=label('out'))
        Instruction(opname='LOAD_NAME', arg=2, argval='y')
        Instruction(label='out',
                    opname='RETURN_VALUE')
    code = builder.code
    if _py3:
        code = types.CodeType(0, 0, 0, 3, 0, code, (), ('x', 'a', 'y'),
                              (), '', '<module>', 1, b'')
    else:
        code = types.CodeType(0, 0, 3, 0, code, (), ('x', 'a', 'y'),
                              (), '', '<module>', 1, '')
    u = Uncompyled(code)
    assert u.ast
    assert u.source == 'return x and a or y'


def test_comprehensions():
    expressions = [
        ('(x for x in this)', None),
        ('(x for x in this if p(x))', None),

        ('[x for x in this]', None),
        ('[x for x in this if p(x)]', None),

        ('((x, y) for x, y in this)', None),
        ('[(x, y) for x, y in this]', None),

        ('((a for a in b) for b in (x for x in this))', None),
        ('[[a for a in b] for b in [x for x in this]]', None),
        ('calling(a for a in this if a < y)', None),
        ('[a for a in x if a < y]', None),
        ('{k: v for k, v in this}', None),
        ('{s for s in this if s < y}', None),
        ('(lambda t: None)(a for x in this)', None),
        # self.env['res.users'].search([])
        ("(user for user in table('res.users'))", None),
        # self.search(cr, uid, [('id', 'not in', no_unlink_ids)])
        ('(which for which in self if which.id not in no_unlik_ids)', None),
        # ('object_merger_model', '=', True)
        ('(which for which in self if which.object_merger_model == True)', None),
        ('(which for which in self if which.object_merger_model)', None),
        # [('stage_id', 'in', ('Done', 'Cancelled')), ('project_id', '=',
        # project.id)]
        ("(project for project in this if project.stage_id in ('Done', 'Cancelled') and project.id == project_id)", None),
        # ['&',
        # '|',
        # ('email_from', '=like', "%%%s" % escape(sender)),   # Ends with _XXX@..
        # ('email_from', '=like', '%%%s>' % escape(sender)),  # or _XXX@..>

        # ('parent_id.parent_id', '=', None),
        # ('res_id', '!=', 0),
        # ('res_id', '!=', None)]
    ]
    _do_test(expressions)


def _do_test(expressions):
    import dis
    from xotl.ql.revenge import Uncompyled

    codes = [
        (
            compile(expr, '<test>', 'eval'),
            expr,
            expected if expected else 'return ' + expr
        )
        for expr, expected in expressions
    ]
    for code, expr, expected in codes:
        u = None
        try:
            u = Uncompyled(code)
            assert u.ast
            assert u.source == expected
        except:
            print()
            print(expr)
            dis.dis(code)
            if u:
                print(u.tokens)
            if u and u.safe_ast:
                print(u.safe_ast)
            raise

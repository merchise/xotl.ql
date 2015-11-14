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

import pytest


def test_scanner_normalization_single_return():
    from xotl.ql.revenge.scanners import InstructionSetBuilder, label
    from xotl.ql.revenge.scanners import keep_single_return

    builder = InstructionSetBuilder()
    with builder() as Instruction:
        Instruction(label='start',
                    opname='LOAD_NAME', arg=0,
                    argval='x', argrepr='x',
                    starts_line=1),
        Instruction(opname='POP_JUMP_IF_FALSE', arg=label('back'),
                    starts_line=None),
        Instruction(opname='LOAD_NAME', arg=1,
                    argval='a', argrepr='a',
                    starts_line=None),
        Instruction(opname='RETURN_VALUE',
                    arg=None, argval=None, argrepr='',
                    starts_line=None),
        Instruction(label='back',
                    opname='LOAD_NAME', arg=2,
                    argval='y', argrepr='y',
                    starts_line=None),
        # Let's make some jumps here but to see other jumps are not affected.
        # Since the return value above takes a single byte but the
        # JUMP_FORWARD takes 3 bytes, all offsets below that point are to be
        # shifted whereas those above will remain.
        Instruction(opname='JUMP_ABSOLUTE', arg=label('back'),
                    starts_line=None)
        Instruction(opname='JUMP_FORWARD', arg=label('next'),
                    starts_line=None),
        Instruction(label='next',
                    opname='FOR_ITER', arg=label('start'), starts_line=None)
        Instruction(opname='RETURN_VALUE', arg=None,
                    argval=None, argrepr='', starts_line=None)
    original = list(builder)

    builder = InstructionSetBuilder()
    with builder() as Instruction:
        Instruction(label='start',
                    opname='LOAD_NAME', arg=0,
                    argval='x', argrepr='x',
                    starts_line=1),
        Instruction(opname='POP_JUMP_IF_FALSE', arg=label('back'),
                    starts_line=None),
        Instruction(opname='LOAD_NAME', arg=1, argval='a', argrepr='a',
                    starts_line=None),
        Instruction(opname='JUMP_FORWARD', arg=label('retval'),
                    starts_line=None),
        Instruction(label='back',
                    opname='LOAD_NAME', arg=2,
                    argval='y', argrepr='y',
                    starts_line=None),
        # Let's make loop here to the instruction just above but to see other
        # jumps are not affected.
        Instruction(opname='JUMP_ABSOLUTE', arg=label('back'),
                    starts_line=None)
        Instruction(opname='JUMP_FORWARD', arg=label('next'),
                    starts_line=None),
        Instruction(label='next',
                    opname='FOR_ITER', arg=label('start'), starts_line=None)
        Instruction(label='retval',
                    opname='RETURN_VALUE', arg=None,
                    argval=None, argrepr='', starts_line=None)
    expected = list(builder)
    assert list(keep_single_return(original)) == expected


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
    from xotl.ql.revenge.scanners import getscanner, without_nops
    from xotl.ql.revenge.scanners import normalize_pypy_conditional

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
    tokens, customize = scanner.disassemble(
        compile('a if x else y', '', 'eval'),
        normalize=(normalize_pypy_conditional, without_nops)
    )
    instructions = [token.instruction for token in tokens if token.instruction]
    assert instructions == expected_program


def test_basic_expressions():
    expressions = [
        'None',
        'Ellipsis',
        'lambda t: None',
        'lambda t: Ellipsis',

        '[1, d]',
        '(1, d)',
        '{1, d}',  # Avoid constants since they're folded by compiler

        'not a',
        '~a',
        '+a',
        '-a',

        'a + b',
        'a & b | c ^ d',
        'a << b >> c',
        'a + b * (d + c)',

        'a in b',
        'a < b in c > d',

        'a.b.c',

        'a[:]',
        'a[s]',
        'a[s:]',
        'a[s::st]',
        'a[:e]',
        'a[:e:st]',
        'a[s:e]',
        'a[s:e:st]',
        'a[::st]',
        'a[:None]',
        'a[None:None:None]',

        'a.attr.b[2:3]',
        'a.attr.b[a[s]:n[l]:s[t]]',

        'c()',
        'c(a)',
        'c(b=1)',
        'c(*args)',
        'c(**kwargs)',
        'c(*args, **kwargs)',

        'c(b=bb(a, i, *a, **kws))(a)',

        'c(a, b=1, *args, **kwargs)',
        'c(a, b=1, *tuple(args), **dict(kwargs))',

        'a[1] + list(b)',

        '{a: b,\n c: d}',
        'lambda x, y=1, *args, **kw: x + y',
        '(lambda x: x)(y)',
    ]
    _do_test(expressions)


@pytest.mark.skipif(not _py3, reason='Syntax only allowed in Python3')
def test_basic_expressions_py3only():
    expressions = [
        '...',   # Ellipsis
        'a[:...]',
        'lambda *, a=1, b=2: a + b',
    ]
    _do_test(expressions)


def test_conditional_expressions():
    expressions = [
        # expr, expected source if different
        'a if x else y',
        'a and b',
        'a or b',
        'a and b and c',
        'a and (b or c)',
        'a and b or c',
        'a or b or c',

        'c(a if x else y)',
        'lambda : (a if x else y)',
        '(lambda: x) if x else (lambda y: y)(y)',
    ]
    _do_test(expressions)


def test_expressions_with_possible_folding():
    expressions = [
        # (expression, (alternatives...))
        ('1 + 3', ('4', )),

        ('None and 1', ('None', )),
        ('None and 1 or 3', ('3', )),
    ]

    _do_test(expressions)


@pytest.mark.xfail()
def test_nested_conditional():
    expressions = [
        '(a if x else y) if (b if z else c) else (d if o else p)',
        '(a if x else y) if (b if z else c) else (d if not o else p)',
        '(a if x else y) if not (b if not z else c) else (d if o else p)',
        '(a if not x else y) if not (b if not z else c) else (d if not o else p)',
    ]
    _do_test(expressions)


def test_conditional_a_la_pypy():
    from xotl.ql.revenge import qst
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
    assert u.safe_ast
    expected = qst.parse('x and a or y')
    try:
        assert u.qst == expected
    except:
        print(u.qst)
        print(expected)


def test_comprehensions():
    expressions = [
        '(x for x in this if not p(x) if z(x))',
        '(x for x in this if not p(x) or z(x))',
        '(x for x in this if not p(x) if z(x))',

        '((x, x + 1) for x in this for y in x if p(y) if not q(x) if z(x))',

        # '[x for x in this]',
        # '[x for x in this if p(x)]',

        '((x, y) for x, y in this)',
        # '[(x, y) for x, y in this]',

        '((a for a in b) for b in (x for x in this))',
        # '[[a for a in b] for b in [x for x in this]]',
        'calling(a for a in this if a < y)',
        # '[a for a in x if a < y]',
        # '{k: v for k, v in this}',
        # '{s for s in this if s < y}',
        '(lambda t: None)(a for x in this)',
    ]
    _do_test(expressions)


def _do_test(expressions, extract=lambda x: x):
    import dis
    from xotl.ql.revenge import Uncompyled, qst

    class alternatives(object):
        def __new__(cls, expr, alt):
            if not isinstance(alt, tuple):
                alt = (alt, )
            res = object.__new__(cls)
            res.alts = [qst.parse(a) for a in alt]
            res.alts.insert(0, qst.parse(expr))
            return res

        def __eq__(self, qst):
            return any(qst == alt for alt in self.alts)

        def __repr__(self):
            return 'Any of:\n'+'\n'.join(str(alt) for alt in self.alts)

    codes = []
    for expr in expressions:
        if isinstance(expr, tuple):
            expr, alts = expr
        else:
            alts = expr
        codes.append((compile(expr, '<test>', 'eval'),
                      expr,
                      alternatives(expr, alts)))
    for code, expr, expected in codes:
        u = None
        try:
            u = Uncompyled(code)
            assert u.safe_ast
            assert expected == u.qst  # compare alternatives first...
            assert compile(u.qst, '', 'eval')  # Ensure we can compile the QST
        except:
            print()
            print(expr)
            dis.dis(code)
            if u:
                print(u.tokens)
            if u and u.safe_ast:
                print(u.safe_ast)
            print('Result:')
            if u and u.safe_qst:
                print(u.safe_qst)
            elif u:
                print('Missing safe qst')
            else:
                print('None')
            print('Expected:')
            print(expected)
            raise


def test_embedded():
    import dis
    from xotl.ql.revenge import Uncompyled

    this = iter([])
    expressions = [
        (a for a in this),    # noqa
    ]
    for expr in expressions:
        try:
            u = Uncompyled(expr.gi_code)
            assert u.ast
        except:
            print()
            print(expr)
            dis.dis(expr.gi_code)
            if u:
                print(u.tokens)
            if u and u.safe_ast:
                print(u.safe_ast)
            raise

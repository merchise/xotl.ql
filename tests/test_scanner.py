#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# ---------------------------------------------------------------------
# test_scanner
# ---------------------------------------------------------------------
# Copyright (c) 2015 Merchise Autrement and Contributors
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the LICENCE attached (see LICENCE file) in the distribution
# package.
#
# Created on 2015-10-29

from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)


def test_scanner_normalization():
    from xotl.ql.revenge.scanners import InstructionSetBuilder, LOAD_NAME
    from xotl.ql.revenge.scanners import POP_JUMP_IF_FALSE, NOP
    from xotl.ql.revenge.scanners import RETURN_VALUE
    from xotl.ql.revenge.scanners import without_nops

    # The PyPy byte code for `a if b else c`:
    builder = InstructionSetBuilder()
    with builder() as Instruction:
        Instruction(opname='LOAD_NAME', opcode=LOAD_NAME,
                    arg=0, argval='x', argrepr='x',
                    starts_line=1, is_jump_target=False),
        Instruction(opname='POP_JUMP_IF_FALSE', opcode=POP_JUMP_IF_FALSE,
                    arg=12, argval=12, argrepr='',
                    starts_line=None, is_jump_target=False),
        Instruction(opname='LOAD_NAME', opcode=LOAD_NAME, arg=1,
                    argval='a', argrepr='a',
                    starts_line=None, is_jump_target=False),
        # Replace the JUMP_FORWARD
        # Instruction(opname='JUMP_FORWARD', opcode=JUMP_FORWARD,
        #             arg=3, argval=15, argrepr='to 15', offset=9,
        #             starts_line=None, is_jump_target=False),
        Instruction(opname='RETURN_VALUE', opcode=RETURN_VALUE, arg=None,
                    argval=None, argrepr='',
                    starts_line=None, is_jump_target=False),
        Instruction(opname='NOP', opcode=NOP, arg=None,
                    argval=None, argrepr='',
                    starts_line=None, is_jump_target=False),
        Instruction(opname='NOP', opcode=NOP, arg=None,
                    argval=None, argrepr='',
                    starts_line=None, is_jump_target=False),
        # End of replacement
        Instruction(opname='LOAD_NAME', opcode=LOAD_NAME,
                    arg=2, argval='y', argrepr='y',
                    starts_line=None, is_jump_target=True),
        Instruction(opname='RETURN_VALUE', opcode=RETURN_VALUE,
                    arg=None, argval=None, argrepr='',
                    starts_line=None, is_jump_target=True)
    modified_pypy_program = list(builder)

    builder = InstructionSetBuilder()
    with builder() as Instruction:
        Instruction(opname='LOAD_NAME', opcode=LOAD_NAME, arg=0,
                    argval='x', argrepr='x',
                    starts_line=1, is_jump_target=False),
        Instruction(opname='POP_JUMP_IF_FALSE', opcode=POP_JUMP_IF_FALSE,
                    arg=10, argval=10, argrepr='',
                    starts_line=None, is_jump_target=False),
        Instruction(opname='LOAD_NAME', opcode=LOAD_NAME, arg=1,
                    argval='a', argrepr='a', offset=6,
                    starts_line=None, is_jump_target=False),
        Instruction(opname='RETURN_VALUE', opcode=RETURN_VALUE,
                    arg=None, argval=None, argrepr='',
                    starts_line=None, is_jump_target=False),
        Instruction(opname='LOAD_NAME', opcode=LOAD_NAME, arg=2,
                    argval='y', argrepr='y',
                    starts_line=None, is_jump_target=True),
        Instruction(opname='RETURN_VALUE', opcode=RETURN_VALUE, arg=None,
                    argval=None, argrepr='', starts_line=None,
                    is_jump_target=False)
    expected = list(builder)
    res = without_nops(modified_pypy_program)
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
    from xotl.ql.revenge.scanners import POP_JUMP_IF_FALSE, LOAD_NAME
    from xotl.ql.revenge.scanners import RETURN_VALUE, getscanner

    # The PyPy byte code for `a if x else y`:
    scanner = getscanner()
    tokens, customize = scanner.disassemble(compile('a if x else y', '', 'eval'))
    instructions = [token.instruction for token in tokens]
    builder = InstructionSetBuilder()
    with builder() as Instruction:
        Instruction(opname='LOAD_NAME',
                    arg=0, argval='x', argrepr='x',
                    offset=0, starts_line=1, is_jump_target=False),
        Instruction(opcode=POP_JUMP_IF_FALSE,
                    arg=label('else y'), starts_line=None,
                    is_jump_target=False),
        Instruction(opname='LOAD_NAME', opcode=LOAD_NAME, arg=1,
                    argval='a', argrepr='a', starts_line=None,
                    is_jump_target=False),
        Instruction(opname='RETURN_VALUE', opcode=RETURN_VALUE,
                    arg=None, argval=None, argrepr='', starts_line=None,
                    is_jump_target=False),
        Instruction(label='else y',
                    opname='LOAD_NAME', opcode=LOAD_NAME,
                    arg=2, argval='y', argrepr='y', starts_line=None),
        Instruction(opname='RETURN_VALUE', opcode=RETURN_VALUE,
                    arg=None, argval=None, argrepr='',
                    starts_line=None)
    expected_program = list(builder)
    assert instructions == expected_program

#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------
# Copyright (c) Merchise Autrement [~º/~] and Contributors
# All rights reserved.
#
# This is free software; you can do what the LICENCE file allows you to.
#

from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)

import pytest

import sys
_pypy = 'PyPy' in sys.version
del sys


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


def test_conditional_a_la_pypy():
    from xotl.ql import qst
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
    code = types.CodeType(0, 0, 0, 3, 0, code, (), ('x', 'a', 'y'),
                          (), '', '<module>', 1, b'')
    u = Uncompyled(code)
    assert u.safe_ast
    expected = qst.parse('x and a or y')
    assert u.qst == expected


def test_embedded():
    from xotl.ql.revenge import Uncompyled

    this = iter([])
    expressions = [
        (a for a in this),    # noqa
    ]
    for expr in expressions:
        u = Uncompyled(expr.gi_code)
        assert u.ast


class Alternatives(object):
    def __new__(cls, expr, alt):
        from xotl.ql import qst
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


def _build_test(expr):
    if isinstance(expr, tuple):
        expr, alts = expr
    else:
        alts = expr

    def test_expr():
        from xotl.ql.revenge import Uncompyled
        sample = expr  # make local so that it appears in error reports.
        code = compile(sample, '', 'eval')
        expected = Alternatives(sample, alts)
        u = Uncompyled(code)
        result = u.qst
        result_ = str(result)
        assert expected == result
        assert compile(result, '', 'eval')
        assert result_
    return test_expr


def _inject_tests(exprs, fmt, wrap=lambda x: x):
    for i, expr in enumerate(exprs):
        _test = wrap(_build_test(expr))
        globals()[fmt % i] = _test


def case(expr, alternatives):
    return (expr, tuple(alternatives))


BASIC_EXPRESSIONS = [
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
_inject_tests(BASIC_EXPRESSIONS, 'test_basic_expressions_%d')

BASIC_EXPRESSIONS_PY3 = [
    '...',   # Ellipsis
    'a[:...]',
    'lambda *, a=1, b=2: a + b',
]
_inject_tests(BASIC_EXPRESSIONS_PY3, 'test_basic_expression_py3only_%d')


CONDITIONAL_EXPRESSIONS = [
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
_inject_tests(CONDITIONAL_EXPRESSIONS, 'test_conditional_expressions_%d')


CONDITIONAL_EXPRESSIONS_FOLDED = [
    case('1 + 3',
         alternatives=['4', ]),

    case('None and 1', alternatives=('None', )),
    case('None and 1 or 3', alternatives=('3', )),
]
_inject_tests(CONDITIONAL_EXPRESSIONS_FOLDED,
              'test_expressions_with_possible_folding_%d')

NESTED_CONDITIONAL_EXPRS = [
    '(a if x else y) if (b if z else c) else (d if o else p)',
    '(a if x else y) if (b if z else c) else (d if not o else p)',
    '(a if x else y) if not (b if not z else c) else (d if o else p)',
    '(a if not x else y) if not (b if not z else c) else (d if not o else p)',
]
_inject_tests(NESTED_CONDITIONAL_EXPRS, 'test_nested_conditional_%d',
              pytest.mark.xfail())


GENEXPRS = [
    case(
        '(x for x in this if not p(x) if z(x))',
        alternatives=(
            '(x for x in this if not p(x) and z(x))',
        )
    ),

    '(x for x in this if not p(x) or z(x))',

    case(
        '(x for x in this for y in x if p(y) if not q(x) if z(x))',
        alternatives=(
            '(x for x in this for y in x if p(y) and not q(x) and z(x))',
            '(x for x in this for y in x if p(y) if not q(x) and z(x))',
            '(x for x in this for y in x if p(y) and not q(x) if z(x))',
        )
    ),

    '((x, y) for x, y in this)',
    '((a for a in b) for b in (x for x in this))',
    'calling(a for a in this if a < y)',
    '(lambda t: None)(a for x in this)',
]
_inject_tests(GENEXPRS, 'test_comprehensions_genexpr_%d')


GENEXPRS_NOT_PYPY = [
    '(x for x in this if not p(x) or z(x) or y(x) or not h(x))',
    '(x for x in this if not p(x) or (z(x) and y(x) and not h(x)))',
]
_inject_tests(GENEXPRS_NOT_PYPY, 'test_comprehensions_genexpr2_%d',
              pytest.mark.xfail(_pypy, reason='Pypy support not completed'))


DICTCOMPS = [
    '{k: v for k, v in this}',

    case(
        '{k: v for k, v in this if not p(k) and p(v)}',
        alternatives=(
            '{k: v for k, v in this if not p(k) if p(v)}',
        ),
    ),

    '{s:f(s) for s in this if not p(s) or z(x)}',
    '{s:v for s in this if p(s) for v in this if not p(v)}',
    '{s:{a for a in b} for s, b in {x for x in this}}',
]
_inject_tests(DICTCOMPS, 'test_comprehensions_dictcomp_%d')

SETCOMPS = [
    case(
        '{s for s in this if not p(s) and z(x)}',
        alternatives=(
            '{s for s in this if not p(s) if z(x)}',
        ),
    ),

    '{s for s in this if not p(s) or z(x)}',
    '{s for s in this if s < y}',
    '{{a for a in b} for b in {x for x in this}}',
]
_inject_tests(SETCOMPS, 'test_comprehensions_setcomp_%d')


NESTED_GENEXPRS = [
    '(y for y in (a for a in this))',
]
_inject_tests(NESTED_GENEXPRS, 'test_nested_genexprs_%d')


LISTCOMPS = [
    '[x for x in this if not p(x) or z(x)]',

    '[x for x in this]',
    '[x for x in this if p(x)]',
    '[a for a in x if a < y]',
    '[(x, y) for x, y in this]',
    '[[a for a in b] for b in [x for x in this]]',
    'calling([a for a in this if a < y])',
    '([child for child in parent.children] for parent in this)',

    case(
        '[x for x in this if not p(x) if z(x)]',
        alternatives=(
            '[x for x in this if not p(x) and z(x)]',
        ),
    ),

]
_inject_tests(LISTCOMPS, 'test_comprehensions_listcomp_%d')


def test_nested_genexprs_ext_1():
    from xotl.ql.revenge import Uncompyled
    this = iter([])

    def nested():
        return (a for a in this)

    expected = (y for y in (a for a in this))
    expected_uncomp = Uncompyled(expected)

    outer = (y for y in nested())
    outer_uncomp = Uncompyled(outer)
    assert outer_uncomp.qst == expected_uncomp.qst

    class Iter():
        def __iter__(self):
            return (a for a in this)
    Iter = Iter()

    outer = (y for y in Iter)
    outer_uncomp = Uncompyled(outer)
    assert outer_uncomp.qst == expected_uncomp.qst


def test_regression_listcomp_as_elt():
    import ast
    from xotl.ql.core import get_query_object, this
    q = get_query_object([child for child in parent.children]
                         for parent in this)
    assert isinstance(q.qst.body.elt, ast.ListComp)

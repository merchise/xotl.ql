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


# We're only testing we can build an AST from the byte-code.  This AST
# extracted from the byte-code directly and not the one we'll provide to
# translators.  The idea is to stabilize the parser from byte-code to this IST
# (Intermediate Syntax Tree).
#
# We'll extend the tests to actually match our target AST.


def test_expressions():
    from xotl.ql.revenge import Uncompyled

    expressions = [
        # expr, expected source if different
        ('(a for a in this if a < y)', None),
        ('a + b', None),
        ('x if x else y', 'if x:\n    return x\nreturn y'),
        ('lambda x, y=1, *args, **kw: x + y', None),
        ('[a for a in x if a < y]', None),
        ('{k: v for k, v in this}', None),
        ('{s for s in this if s < y}', None),
        ('c(a)', None),
        ('a and b or c', None),
        ('a & b | c ^ d', None),
        ('a << b >> c', None),
        ('a + b * (d + c)', None),
        ('a.attr.b[2:3]', None),
        ('a[1] + list(b)', None)
    ]
    codes = [(compile(expr, '<test>', 'eval'), expr, expected if expected else 'return ' + expr)
             for expr, expected in expressions]
    failures = []
    for code, expr, expected in codes:
        try:
            u = Uncompyled(code)
            assert u.source == expected
        except AssertionError:
            raise
        except Exception as error:
            failures.append((expr, error))
    assert not failures

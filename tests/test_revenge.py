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
        '(a for a in this if a < y)',
        'a + b',
        'x if x else y',
        'lambda x, y=1, *args, **kw: x + y',
        '[a for a in x if a < y]',
        '{k: v for k, v in this}',
        '{s for s in this if s < y}',
        'c(a)',
        'a.attr.b[2:3]',
        'a[1] + list(b)',
    ]
    codes = [(compile(expr, '<test>', 'eval'), expr) for expr in expressions]
    failures = []
    for code, expr in codes:
        try:
            Uncompyled(code)
        except Exception as error:
            failures.append((expr, error))
    assert not failures

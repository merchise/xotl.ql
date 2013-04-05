#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#----------------------------------------------------------------------
# translation_utils
#----------------------------------------------------------------------
# Copyright (c) 2013 Merchise Autrement and Contributors
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under
# the terms of the LICENCE attached in the distribution package.
#
# Created on 2013-04-05

from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        unicode_literals as _py3_unicode,
                        absolute_import as _py3_abs_imports)


import pytest
import functools

from xoutil.context import context
from xoutil.proxy import UNPROXIFING_CONTEXT

from xotl.ql import this, these, thesefy
from xotl.ql.translation import get_term_path, get_term_signature
from xotl.ql import translation

__author__ = "Manuel Vázquez Acosta <mva.led@gmail.com>"
__date__   = "Fri Apr  5 09:16:21 2013"


@pytest.mark.xfail(str("sys.version.find('PyPy') != -1"))
def test_get_term_path():
    assert get_term_path(this.a.b.c) == (None, 'a', 'b', 'c')
    assert get_term_path(this) == (None, )
    assert get_term_path(this('x').a.b.c) == ('x', 'a', 'b', 'c')


@pytest.mark.xfail(str("sys.version.find('PyPy') != -1"))
def test_get_term_signature():
    assert get_term_signature(this.a) == ((), (None, 'a'))

    query = these(child
                  for parent in this('parent')
                  for child in parent.children)
    term = query.selection
    assert get_term_signature(term) == (('parent', 'children'), ('parent', 'children'))

    term = query.tokens[0].expression
    assert get_term_signature(term) == (('parent', ), ('parent', ))

    term = query.tokens[1].expression
    assert get_term_signature(term) == (('parent', 'children'), ('parent', 'children'))


def test_sorting_with_cmp():
    @thesefy
    class Person(object): pass

    query = these((who, who2) for who in Person for who2 in Person)

    # Sort with tokens + filters
    sorted_parts =  list(sorted(query.tokens + query.filters,
                                key=functools.cmp_to_key(translation.cmp)))

    _k = functools.cmp_to_key(translation.cmp)
    for i, part in enumerate(sorted_parts):
        if i < len(sorted_parts) + 1:
            for after in sorted_parts[i+1:]:
                assert _k(part) <= _k(after), (part, after)


    # Now sort with filters + tokens
    sorted_parts =  list(sorted(query.filters + query.tokens,
                                key=functools.cmp_to_key(translation.cmp)))

    _k = functools.cmp_to_key(translation.cmp)
    for i, part in enumerate(sorted_parts):
        if i < len(sorted_parts) + 1:
            for after in sorted_parts[i+1:]:
                assert _k(part) <= _k(after), (part, after)

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


from hypothesis import given
from hypothesis.strategies import lists, integers

from xotl.ql.tools import detect_names
from xotl.ql.revenge.tools import lastindex


def test_freenames_detection_1():
    result = detect_names('all(x for x in this for y in those if p(y)'
                          '      for z in y)')
    expected = {'this', 'those', 'p', 'all'}
    assert result == expected


def test_freenames_detection_2():
    result = detect_names('(lambda x: lambda p, y=p(x): x + y)(x)')
    expected = {'p', 'x'}  # p is the free var at y=p(x), not the lambda arg.
    assert result == expected

    # The same test but make it clear that, the free `p` (here `f`) is not the
    # same as the arg.
    result = detect_names('(lambda x: lambda p, y=f(x): x + y)(x)')
    expected = {'f', 'x'}
    assert result == expected


small_integers = integers(min_value=-50, max_value=50)
int_lists = lists(small_integers, min_size=10, average_size=100)
lists_and_index = int_lists.map(
    lambda l: (l, integers(min_value=0, max_value=len(l)-1).example())
)


@given(lists_and_index)
def test_lastindex(arg):
    lst, index = arg
    which = lst[index]
    assert lastindex(lst, which) == _evident_findlast(lst, which)


@given(int_lists)
def test_lastindex_misses(lst):
    try:
        lastindex(lst, object())  # In a list of numbers there's no object()
    except ValueError:
        pass
    else:
        assert False


def _evident_findlast(lst, which):
    pos = lst.index(which)
    # pos, holds the first occurrence, lets find other and break when there
    # are no more:
    while True:
        try:
            pos = lst.index(which, pos + 1)
        except ValueError:
            break
    return pos

#!/usr/bin/env python3.6
# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------
# Copyright (c) Merchise Autrement [~º/~] and Contributors
# All rights reserved.
#
# This is free software; you can do what the LICENCE file allows you to.
#

import sys
import pytest
from xoutil.future.textwrap import dedent
from xotl.ql.translation.py import _TestPlan as translate

from . import world   # noqa: ensure there are some persons in the VM memory


if sys.version_info >= (3, 6):
    exec(dedent(r'''
    def get_fstring_projections_query():
        from xotl.ql.core import this
        from .model import Person
        return (
            f"My name is {who.name}"
            for who in this
            if isinstance(who, Person)
        )
    '''))


@pytest.mark.skipif(sys.version_info < (3, 6),
                    reason='f-strings are Python 3.6+')
def test_fstring_projections():
    query = get_fstring_projections_query()   # noqa
    plan = translate(query)
    result = set(plan())
    assert 'My name is Carli' in result

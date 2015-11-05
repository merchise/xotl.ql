#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# ---------------------------------------------------------------------
# test_qst
# ---------------------------------------------------------------------
# Copyright (c) 2015 Merchise Autrement and Contributors
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the LICENCE attached (see LICENCE file) in the distribution
# package.
#
# Created on 2015-11-05


from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)


from xotl.ql.revenge import qst


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
        ('a and b or c', None),
        ('(a if x else y) if (b if z else c) else (d if o else p)', None),
        ('(a if x else y) if not (b if not z else c) else (d if o else p)', None),
        ('c(a if x else y)', None),
        ('lambda : (a if x else y)', None),
        ('(lambda: x) if x else (lambda y: y)(y)', None),
    ]
    _do_test(expressions)


def test_comprehensions():
    expressions = [
        ('((x, y) for x, y in this)', None),
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
    codes = [
        (
            qst.parse(expr, '<test>'),
            expr,
            qst.pyast.parse(expr, '<test>', 'eval')
        )
        for expr, _expected in expressions
    ]
    for qst_, expr, ast in codes:
        assert qst_ == ast

#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# ---------------------------------------------------------------------
# _infinity
# ---------------------------------------------------------------------
# Copyright (c) 2016 Merchise Autrement and Contributors
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the LICENCE attached (see LICENCE file) in the distribution
# package.
#
# Created on 2016-07-04

'''The Infinity value.

Usage::

   >>> Infinity > 98**76
   True

   >>> -Infinity < -98**76
   True

   >>> -Infinity < Infinity
   True

This value does not support addition and other arithmetical operations::

   >>> Infinity + 3  # +doctest: +ELLIPSIS
   Traceback (most recent call last)
   ...
   TypeError: unsupported operand type(s) for +: 'InfinityType' and 'int'

'''

from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)


try:
    from xoutil.infinity import Infinity  # TODO: migrate
except ImportError:
    from functools import total_ordering

    @total_ordering
    class InfinityType(object):
        _positive = None
        _negative = None

        def __new__(cls, sign):
            if sign < 0:
                res = cls._negative
                if not res:
                    cls._negative = res = object.__new__(cls)
                    res.sign = -1
            else:
                res = cls._positive
                if not res:
                    cls._positive = res = object.__new__(cls)
                    res.sign = 1
            return res

        def __init__(self, sign):
            self.sign = -1 if sign < 0 else 1

        def __lt__(self, other):
            from numbers import Number
            if isinstance(other, Number):
                return self.sign < 0   # True iff -Infinity
            elif isinstance(other, InfinityType):
                return self.sign < other.sign
            else:
                raise TypeError('Incomparable types')

        def __eq__(self, other):
            from numbers import Number
            if isinstance(other, Number):
                return False
            elif isinstance(other, InfinityType):
                return self.sign == other.sign
            else:
                raise TypeError('Incomparable types')

        def __neg__(self):
            return type(self)(-self.sign)

        def __str__(self):
            return '∞' if self.sign > 0 else '-∞'

        def __repr__(self):
            return 'Infinity' if self.sign > 0 else '-Infinity'

    Infinity = InfinityType(+1)

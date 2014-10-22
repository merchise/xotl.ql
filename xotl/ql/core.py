#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#----------------------------------------------------------------------
# xotl.ql.core
#----------------------------------------------------------------------
# Copyright (c) 2012-2014 Merchise Autrement and Contributors
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under
# the terms of the LICENCE attached in the distribution package.
#
# Created on May 24, 2012


'''The query language core.

'''

from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)


class universe(object):
    def __new__(cls):
        res = getattr(cls, 'instance', None)
        if not res:
            res = super(universe, cls).__new__(cls)
            cls.instance = res
        return res

    def __getitem__(self, key):
        return self

    def __getattr__(self, name):
        return self

    def __iter__(self):
        return self

    def next(self):
        raise StopIteration
    __next__ = next

this = universe()


def these(generator):
    pass


def thesefy(cls):
    return cls

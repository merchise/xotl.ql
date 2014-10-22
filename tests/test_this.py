#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#----------------------------------------------------------------------
# xotl.ql.tests.test_this
#----------------------------------------------------------------------
# Copyright (c) 2012-2014 Merchise Autrement
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under
# the terms of the LICENCE attached in the distribution package.
#
# Created on May 25, 2012

from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        unicode_literals as _py3_unicode,
                        absolute_import as _py3_abs_import)

import unittest


class TestThisObject(unittest.TestCase):
    def test_this_uniqueness(self):
        from xotl.ql import this
        from xotl.ql.core import universe

        self.assertIs(this, universe())
        self.assertIs(this, this.whatever[:90])

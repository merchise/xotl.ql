#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#----------------------------------------------------------------------
# tests.test_thesefy
#----------------------------------------------------------------------
# Copyright (c) 2013 Merchise Autrement and Contributors
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under
# the terms of the LICENCE attached in the distribution package.
#
# Created on 2013-04-11

from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        unicode_literals as _py3_unicode,
                        absolute_import as _py3_abs_imports)


from xotl.ql import thesefy

__author__ = "Manuel Vázquez Acosta <mva.led@gmail.com>"
__date__   = "Thu Apr 11 08:21:27 2013"



def test_regression_thesefy_should_not_affect_super():
    class Base(object):
        def echo(self, what):
            return what


    @thesefy
    class Classy(Base):
        def echo(self, what):
            res = super(Classy, self).echo(what)
            return res

    objy = Classy()
    assert objy.echo(1) == 1

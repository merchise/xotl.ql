#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# ---------------------------------------------------------------------
# exceptions
# ---------------------------------------------------------------------
# Copyright (c) 2015, 2016 Merchise Autrement and Contributors
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the LICENCE attached (see LICENCE file) in the distribution
# package.
#
# Created on 2015-11-05

from __future__ import absolute_import as _py3_abs_import


class RevengeError(Exception):
    '''The base error for all revenge errors.'''


class ScannerError(RevengeError):
    '''Error invalid byte-code.'''


class ScannerAssertionError(RevengeError, AssertionError):
    pass


class ParserError(RevengeError):
    '''Cannot make up an expression from the stream of byte-code.'''


class ParserAssertionError(RevengeError, AssertionError):
    pass

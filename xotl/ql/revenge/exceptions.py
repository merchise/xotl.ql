#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------
# Copyright (c) Merchise Autrement [~º/~] and Contributors
# All rights reserved.
#
# This is free software; you can do what the LICENCE file allows you to.
#


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

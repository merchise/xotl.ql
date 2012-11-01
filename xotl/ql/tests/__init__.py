#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#----------------------------------------------------------------------
# xotl.ql.tests.__init__
#----------------------------------------------------------------------
# Copyright (c) 2012 Merchise Autrement
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the LICENCE attached in the distribution package.
#
# Created on Oct 31, 2012


from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        unicode_literals as _py3_unicode,
                        absolute_import as _py3_abs_imports)

import logging

from xoutil.compat import inspect_getfullargspec, iteritems_
from xoutil.objects import nameof
from xoutil.aop.classical import weave

__docstring_format__ = 'rst'
__author__ = 'manu'


class LoggingAspect(object):
    def _after_(self, method, result, exc_value, *args, **kwargs):
        cls = nameof(type(self)) if self else None
        if cls:
            method_name = '{cls}.{method}'.format(cls=cls, method=nameof(method))
        else:
            method_name = nameof(method)
        if self:
            args = (self, ) + args
        arguments = ', '.join('%r' % a for a in args) if args else ''
        if kwargs:
            arguments += ', '.join('%s=%r' % (k, v)
                                   for k, v in iteritems_(kwargs))
        message = 'Called {method}({arguments})'.format(method=method_name,
                                                         arguments=arguments)
        logger = logging.getLogger(cls)
        logger.info(message)
        print(message)
        if result is not None:
            logger.info('Result: %r' % result)
            print('Result: %r' % result)
        return result



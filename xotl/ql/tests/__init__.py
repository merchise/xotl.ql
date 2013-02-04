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
import threading

from xoutil.compat import inspect_getfullargspec, iteritems_
from xoutil.objects import nameof
from xoutil.aop.classical import weave

__docstring_format__ = 'rst'
__author__ = 'manu'


thread_local = threading.local()


def logging_aspect(output=None):
    '''
    Creates a logging "aspect" that logs entries to `output`. If `output` is
    None, the standard logging output will be used.
    '''
    class LoggingAspect(object):
        @classmethod
        def get_padding(cls):
            return getattr(thread_local, 'padding', 0)

        @classmethod
        def increase_padding(cls):
            padding = cls.get_padding()
            cls.set_padding(padding + 1)
            return padding + 1

        @classmethod
        def decrease_padding(cls):
            padding = cls.get_padding()
            if padding:
                cls.set_padding(padding - 1)
                return padding - 1
            else:
                return padding

        @classmethod
        def set_padding(cls, value):
            thread_local.padding = value

        @classmethod
        def log_for(cls, self, message):
            clsname = nameof(type(self)) if self else None
            logger = logging.getLogger(clsname)
            logger.setLevel(logging.DEBUG)
            if output and not logger.handlers:
                logger.addHandler(logging.StreamHandler(output))
            logger.debug(message)

        @classmethod
        def log_signature(cls, self, method, *args, **kwargs):
            if self:
                # Since many of our objects implement __getattribute__, we get
                # into an infinite recursion, so let's avoid calling str and
                # repr.
                args = (('<{0} at {1:#x}>'.format(nameof(type(self)),
                                                  id(self)), ) + args)
            arguments = ', '.join('%r' % a for a in args) if args else ''
            if kwargs:
                arguments += ', '.join('%s=%r' % (k, v)
                                       for k, v in iteritems_(kwargs))
            if self:
                method_name = '{cls}.{method}'.format(cls=type(self),
                                                      method=nameof(method))
            else:
                method_name = nameof(method)
            message = '\t' * cls.get_padding()
            message += ('Calling {method}({arguments}) ...'.
                        format(method=method_name, arguments=arguments))
            cls.log_for(type(self) if self else None, message)

        @classmethod
        def log_cpy_context(cls, self, context=4):
            import sys
            import inspect
            frame = sys._getframe(4)
            try:
                _fname, _lno, _fn, code, _idx = inspect.getframeinfo(frame,
                                                                     context)
                cls.log_for(self, code)
            finally:
                del frame

        @classmethod
        def log_return(cls, self, method, result):
            message = '\t' * cls.get_padding()
            message = '... returned {0}'.format(result)
            cls.log_for(self, message)

        @classmethod
        def log_exception(cls, self, method, error):
            if self:
                method_name = '{cls}.{method}'.format(cls=type(self),
                                                      method=nameof(method))
            else:
                method_name = nameof(method)
            message = '\t' * cls.get_padding()
            message = 'An exception occurred when calling {0}'.format(method_name)
            cls.log_for(self, message)

        def _around_(self, method, *args, **kwargs):
            LoggingAspect.log_signature(self, method, *args, **kwargs)
            LoggingAspect.log_cpy_context(self)
            try:
                LoggingAspect.increase_padding()
                try:
                    result = method(*args, **kwargs)
                finally:
                    LoggingAspect.decrease_padding()
                LoggingAspect.log_return(self, method, result)
                return result
            except Exception as error:
                LoggingAspect.log_exception(self, method, error)
                raise
    return LoggingAspect

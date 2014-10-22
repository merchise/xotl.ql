#!/usr/bin/env python
# -*- coding: utf-8 -*-
#----------------------------------------------------------------------
# xotl.ql.release
#----------------------------------------------------------------------
# Copyright (c) 2012-2014 Merchise Autrement and Contributors
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under
# the terms of the LICENCE attached in the distribution package.
#
# Created on 2012-06-29

from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)


VERSION = '0.3.0'


def dev_tag():
    result = ''
    import os
    fn = os.path.abspath(os.path.join(__file__, '..', '..', '..', 'setup.cfg'))
    if os.path.exists(fn):
        try:
            import configparser
        except:
            import ConfigParser as configparser
        parser = configparser.SafeConfigParser()
        parser.read([fn])
        try:
            res = parser.get(str('egg_info'), str('tag_build'))
        except:
            res = None
        if res:
            result = res
    return result

RELEASE_TAG = dev_tag()

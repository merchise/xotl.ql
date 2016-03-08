#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------
# xotl.ql.release
# ---------------------------------------------------------------------
# Copyright (c) 2012-2016 Merchise Autrement and Contributors
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


def dev_tag_installed():
    import pkg_resources
    try:
        dist = pkg_resources.get_distribution('xotl')
        full_version = dist.version
        # FIX: Below line is not working anymore
        base = dist.parsed_version.base_version
        return full_version[len(base):]
    except:
        return None

RELEASE_TAG = dev_tag_installed() or ''

# I won't put the release tag in the version_info tuple.  Since PEP440 is on
# the way.
VERSION_INFO = tuple(int(x) for x in VERSION.split('.'))

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------
# Copyright (c) Merchise Autrement [~º/~] and Contributors
# All rights reserved.
#
# This is free software; you can do what the LICENCE file allows you to.
#

VERSION = '0.6.0'


def dev_tag_installed():
    import pkg_resources
    try:
        dist = pkg_resources.get_distribution('xotl.ql')
        full_version = dist.version
        # FIX: Below line is not working anymore
        base = dist.parsed_version.base_version
        return full_version[len(base):]
    except Exception:
        return None


RELEASE_TAG = dev_tag_installed() or ''

# I won't put the release tag in the version_info tuple.  Since PEP440 is on
# the way.
VERSION_INFO = tuple(int(x) for x in VERSION.split('.'))

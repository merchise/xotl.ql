#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# ---------------------------------------------------------------------
# _util
# ---------------------------------------------------------------------
# Copyright (c) 2016 Merchise Autrement and Contributors
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the LICENCE attached (see LICENCE file) in the distribution
# package.
#
# Created on 2016-03-04

from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)

import importlib
from xoutil.eight import string_types


try:
    from xoutil.objects import import_object   # TODO: migrate
except ImportError:
    def import_object(name, package=None,
                      sep='.', default=None, **kwargs):
        """Get symbol by qualified name.

        The name should be the full dot-separated path to the class::

            modulename.ClassName

        Example::

            xotl.ql.core.QueryObject
                        ^- class name

        or using ':' to separate module and symbol::

            xotl.ql.core:QueryObject

        Examples:

            >>> import_object('xotl.ql.core.QueryObject')
            <class 'xotl.ql.core.QueryObject'>

            # Does not try to look up non-string names.
            >>> from xotl.ql.core import QueryObject
            >>> import_object(QueryObject) is QueryObject
            True

        """
        imp = importlib.import_module
        if not isinstance(name, string_types):
            return name                                 # already a class
        sep = ':' if ':' in name else sep
        module_name, _, cls_name = name.rpartition(sep)
        if not module_name:
            cls_name, module_name = None, package if package else cls_name
        try:
            module = imp(module_name, package=package, **kwargs)
            return getattr(module, cls_name) if cls_name else module
        except (ImportError, AttributeError):
            if default is None:
                raise
        return default

#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# ---------------------------------------------------------------------
# xotl.ql.translation
# ---------------------------------------------------------------------
# Copyright (c) 2012-2016 Merchise Autrement and Contributors
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under
# the terms of the LICENCE attached in the distribution package.
#
# Created on Jul 2, 2012

'''The main purposes of this module are two:

- To provide common query/expression translation framework from query
  objects to data store languages.

- To provide a testing bed for queries to retrieve real objects from
  somewhere (in this case the Python's).

'''

from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)

from xotl.ql.interfaces import Interface


class TranslationError(TypeError):
    '''A translation error.

    Translators should issue this kind of exception if there is an error in
    the query that impedes the translation.

    The query should not be retried if not changed.

    '''


def _instance_of(which):
    '''Returns an `accept` filter for :func:`_iter_objects` or
    :func:`_iter_classes` that only accepts objects that are instances of
    `which`; `which` may be either a class or an Interface
    (:mod:`!zope.interface`).

    '''
    def accept(ob):
        return (isinstance(ob, which) or
                (issubclass(which, Interface) and which.providedBy(ob)))
    return accept


def _is_instance_of(who, *types):
    '''Tests is who is an instance of any `types`. `types` may contains both
    classes and Interfaces.

    '''
    return any(_instance_of(w)(who) for w in types)

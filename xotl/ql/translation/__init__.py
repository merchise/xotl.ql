#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------
# Copyright (c) Merchise Autrement [~º/~] and Contributors
# All rights reserved.
#
# This is free software; you can do what the LICENCE file allows you to.
#

'''The main purposes of this module are two:

- To provide common query/expression translation framework from query
  objects to data store languages.

- To provide a testing bed for queries to retrieve real objects from
  somewhere (in this case the Python's).

'''

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

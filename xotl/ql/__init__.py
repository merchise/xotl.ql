#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------
# Copyright (c) Merchise Autrement [~º/~] and Contributors
# All rights reserved.
#
# This is free software; you can do what the LICENCE file allows you to.
#

'''A pythonic Query Language.

This package provides an abstract query language based on comprehesions. The
sole goal of this package is to provide the Abstract Synxtax Tree for the
queries produced using this language.

The query language is composed by only two modules:

- The :mod:`xotl.ql.expressions` module that defines the core for
  defining expressions in this language.

- The :mod:`xotl.ql.core` module defines the entry point for the
  query language and documents it extensively.

There's third module :mod:`~xotl.ql.translate` that has some tools for
aiding the translation of queries in to query plans for real data
stores.

'''

from .core import this, get_query_object, thesefy, normalize_query  # noqa
from .revenge import qst   # noqa

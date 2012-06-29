#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# --------------------------------------------------
# xotl.ql
# --------------------------------------------------
# Copyright (c) 2012 Merchise Autrement
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License (GPL) as published by the
# Free Software Foundation;  either version 2  of  the  License, or (at
# your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA 02110-1301, USA.
#
# Created on May 24, 2012

'''
A pythonic Query Language (Ql).

This package provides an abstract query language based on comprehesions. The
sole goal of this package is to provide the Abstract Synxtax Tree for the
queries produced using this language.

The query language is composed by only two modules:

- The :mod:`~xotl.ql.expressions` module that defines the core for defining
  expressions in this language.

- The :mod:`~xotl.ql.these` module defines the entry point for the query
  language and documents it extensively.

'''

from . import expressions
from .these import this

__all__ = (b'this', b'expressions')

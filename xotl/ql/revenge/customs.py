#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------
# Copyright (c) Merchise Autrement [~º/~] and Contributors
# All rights reserved.
#
# This is free software; you can do what the LICENCE file allows you to.
#

'''Custom rules for customized tokens.

'''

from .eight import _py_version, override


NOP = lambda self, args: None


@override((3, 5) <= _py_version < (3, 6))
def MAKE_FUNCTION(self, op, k, v):
    '''Pushes a new function object on the stack.  From bottom to top, the
    consumed stack must consist of

    * ``argc & 0xFF`` default argument objects in positional order

    * ``(argc >> 8) & 0xFF`` pairs of name and default argument, with the name
     just below the object on the stack, for keyword-only parameters

    * ``(argc >> 16) & 0x7FFF`` parameter annotation objects

    * a tuple listing the parameter names for the annotations (only if there are
     ony annotation objects)

    * the code associated with the function (at TOS1)

    * the :term:`qualified name` of the function (at TOS)

    '''
    ndefaults = v & 0xFF
    nkwonly = (v >> 8) & 0xFF
    nannotations = (v >> 16) & 0x7FFF
    assert nannotations == 0
    self.add_rule(
        'mklambda ::= %s %s _py_load_lambda %s' % (
            'expr ' * ndefaults, 'kwarg ' * nkwonly, k),
        NOP
    )


@MAKE_FUNCTION.override((3, 6) <= _py_version)
def MAKE_FUNCTION(self, op, k, v):
    # TODO:
    # MAKE_FUNCTION (argc)
    #
    # Pushes a new function object on the stack.  From bottom
    # to top, the consumed stack must consist of values if the
    # argument carries a specified flag value
    #
    # * ``0x01`` a tuple of default argument objects in
    #   positional order
    # * ``0x02`` a dictionary of keyword-only parameters'
    #   default values
    # * ``0x04`` an annotation dictionary
    # * ``0x08`` a tuple containing cells for free variables,
    #   making a closure
    # * the code associated with the function (at TOS1)
    # * the :term:`qualified name` of the function (at TOS)
    pass

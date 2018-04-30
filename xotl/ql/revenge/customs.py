#!/usr/bin/env python3
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

    * a tuple listing the parameter names for the annotations (only if there
     are any annotation objects)

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
    posdefaults = 'expr ' if v & 0x01 else ''
    kwdefaults = 'expr ' if v & 0x02 else ''
    annotations = 'expr ' if v & 0x04 else ''
    cells = 'expr ' if v & 0x08 else ''
    rule = 'mklambda ::= {posdefaults}{kwdefaults}{annotations}{cells} _py_load_lambda ' + k
    return rule.format(
        posdefaults=posdefaults,
        kwdefaults=kwdefaults,
        annotations=annotations,
        cells=cells
    )


@override((3, 5) <= _py_version < (3, 6))
def CALL_FUNCTION(self, op, k, v):
    na = (v & 0xff)           # positional parameters
    nk = (v >> 8) & 0xff      # keyword parameters
    rule = 'call_function ::= expr ' + 'expr ' * na
    if op in ('CALL_FUNCTION_VAR', 'CALL_FUNCTION_VAR_KW'):
        # Add the *arg
        rule += 'stararg_expr '
    rule += 'kwarg ' * nk
    if op in ('CALL_FUNCTION_VAR_KW', 'CALL_FUNCTION_KW'):
        rule += 'kwarg_expr '
    rule += k
    return rule


CALL_FUNCTION_VAR = CALL_FUNCTION_KW = CALL_FUNCTION_VAR_KW = CALL_FUNCTION


@CALL_FUNCTION.override((3, 6) <= _py_version)
def CALL_FUNCTION(self, opcode, token, argc):
    # Since Python 3.6:
    #   This opcode is used only for calls with positional arguments.
    #
    # Calls a function.  *argc* indicates the number of positional arguments.
    # The positional arguments are on the stack, with the right-most argument
    # on top.  Below the arguments, the function object to call is on the
    # stack.  Pops all function arguments, and the function itself off the
    # stack, and pushes the return value.
    return 'call_function36 ::= expr ' + 'expr ' * argc + token


@CALL_FUNCTION.override((3, 6) <= _py_version)
def CALL_FUNCTION_KW(self, opcode, token, argc):
    # Since Python 3.6:
    #
    # Calls a function.  *argc* indicates the number of arguments (positional
    # and keyword).  The top element on the stack contains a tuple of keyword
    # argument names.  Below the tuple, keyword arguments are on the stack, in
    # the order corresponding to the tuple.  Below the keyword arguments, the
    # positional arguments are on the stack, with the right-most parameter on
    # top.  Below the arguments, the function object to call is on the stack.
    # Pops all function arguments, and the function itself off the stack, and
    # pushes the return value.
    #
    # .. versionchanged:: 3.6
    #    Keyword arguments are packed in a tuple instead of a dictionary,
    #    *argc* indicates the total number of arguments
    #
    return 'call_function36_kw ::= expr ' + 'expr ' * (argc + 1) + token


@CALL_FUNCTION.override((3, 6) <= _py_version)
def CALL_FUNCTION_EX(self, opcode, token, argc):
    # Calls a function. The lowest bit of *flags* indicates whether the
    # var-keyword argument is placed at the top of the stack.  Below the
    # var-keyword argument, the var-positional argument is on the stack.
    # Below the arguments, the function object to call is placed.  Pops all
    # function arguments, and the function itself off the stack, and pushes
    # the return value. Note that this opcode pops at most three items from
    # the stack. Var-positional and var-keyword arguments are packed by
    # :opcode:`BUILD_TUPLE_UNPACK_WITH_CALL` and
    # :opcode:`BUILD_MAP_UNPACK_WITH_CALL`.
    varkwarg = 1 if argc & 0x01 else 0
    rule = 'call_function36_ex ::= expr _fn_ex_args ' + '_fn_ex_kwargs ' * varkwarg + token
    return rule


def BUILD_MAP_UNPACK_WITH_CALL(self, opcode, token, count):
    if _py_version < (3, 6):
        count = count & 0xFF
    return '_map_unpack ::= ' + 'expr ' * count + token


@override((3, 6) <= _py_version)
def BUILD_STRING(self, opcode, token, count):
    return 'formatted_string ::= ' + 'expr ' * count + token

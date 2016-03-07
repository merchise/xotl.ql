# -*- encoding: utf-8 -*-
# ---------------------------------------------------------------------
# xotl.ql.revenge.eight
# ---------------------------------------------------------------------
# Copyright (c) 2014-2016 Merchise Autrement and Contributors
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the LICENCE attached (see LICENCE file) in the distribution
# package.
#
# Created on 2014-04-08

'''Utility for defining methods variants.

Method variants allow several implementations of a single method to be chosen
given several conditions are met *when the module/class is being created*.
Notice this is not dynamic dispatching à la functional programming.


'''

from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)

import sys

from xoutil import types


# Python predicates
prepy27 = sys.version_info < (2, 7)
py27 = (2, 7) <= sys.version_info < (3, 0)
py30 = (3, 0) <= sys.version_info < (3, 1)
py31 = (3, 1) <= sys.version_info < (3, 2)
py32 = (3, 2) <= sys.version_info < (3, 3)
py33 = (3, 3) <= sys.version_info < (3, 4)
py34 = (3, 4) <= sys.version_info < (3, 5)
py35 = (3, 5) <= sys.version_info   # XXX: Not released as of today

py2k = py27 or prepy27
py3k = (3, 0) <= sys.version_info < (4, 0)

pypy = sys.version.find('PyPy') >= 0
_py_version = sys.version_info


class unimplemented(object):
    '''Not implemented stub for `override`:func:.'''
    @staticmethod
    def override(pred):
        return override(pred=pred)

    def __init__(self, *args, **kwargs):
        raise TypeError


def override(pred=True, default=None):
    '''Allow overriding of `target`.

    If the predicated given by `pred` is True, the `target` is returned, but
    gains an `override` method to allowing chaining of overrides.

    The last defined `override` that matches `pred` wins.

    Intended usage::

        @override(py27)
        def foobar(x):
            print(x, 'Python 2.7')

        @foobar.override(prepy27)   # In python 2.7, keeps the previous def
        def foobar(x):
           print(x, 'An older python')

        @foobar.override(py30)
        def foobar(x):
            print(x, 'Python 3.0 but not bigger')

        @foobar.override(py3k)  # shadows the previous definition
        def foobar(x):
           print(x, 'Any python 3')


    .. warning:: This is not dynamic dispatching.  The predicated is evaluated
       only at function creation the returned function is thus, the variant
       that matched its predicate or the `unimplemented`:class: stub.

    '''
    def deco(target):
        def passed(p):
            if isinstance(p, types.FunctionType):
                result = p()
            else:
                result = p
            return result

        if passed(pred):
            target.override = lambda *a, **kw: override(default=target, *a, **kw)  # noqa
            return target
        else:
            return default or unimplemented
    return deco


# Python 2 port for dis.Bytecode and Instruction...
try:
    from dis import Bytecode, Instruction, _Instruction
except ImportError:
    try:
        from xoutil.params import keywordonly   # migrate
    except ImportError:
        keywordonly = lambda *names: lambda f: f

    def _ord(i):
        if isinstance(i, int):
            return i
        else:
            return ord(i)

    class Bytecode(object):
        """The bytecode operations of a piece of code

        Instantiate this with a function, method, string of code, or a code
        object (as returned by compile()).

        Iterating over this yields the bytecode operations as Instruction
        instances.

        """
        @keywordonly('first_line', 'current_offset')
        def __init__(self, x, first_line=None, current_offset=None):
            self.codeobj = co = _get_code_object(x)
            if first_line is None:
                self.first_line = co.co_firstlineno
                self._line_offset = 0
            else:
                self.first_line = first_line
                self._line_offset = first_line - co.co_firstlineno
            self._cell_names = co.co_cellvars + co.co_freevars
            self._linestarts = dict(findlinestarts(co))
            self._original_object = x
            self.current_offset = current_offset

        def __iter__(self):
            co = self.codeobj
            return _get_instructions_bytes(co.co_code, co.co_varnames,
                                           co.co_names,
                                           co.co_consts, self._cell_names,
                                           self._linestarts,
                                           line_offset=self._line_offset)

        def __repr__(self):
            return "{}({!r})".format(self.__class__.__name__,
                                     self._original_object)

        @classmethod
        def from_traceback(cls, tb):
            """ Construct a Bytecode from the given traceback """
            while tb.tb_next:
                tb = tb.tb_next
            return cls(tb.tb_frame.f_code, current_offset=tb.tb_lasti)

        def info(self):
            """Return formatted information about the code object."""
            return _format_code_info(self.codeobj)

    def _get_code_object(x):
        """Helper to handle methods, functions, generators, strings and
        raw code objects.

        """
        if hasattr(x, '__func__'):  # Method
            x = x.__func__
        if hasattr(x, 'func_code'):  # Function
            x = x.__code__
        if hasattr(x, 'gi_code'):  # Generator
            x = x.gi_code
        if isinstance(x, str):     # Source code
            x = _try_compile(x, "<disassembly>")
        if hasattr(x, 'co_code'):  # Code object
            return x
        raise TypeError("don't know how to disassemble %s objects" %
                        type(x).__name__)

    def _try_compile(source, name):
        """Attempts to compile the given source, first as an expression and
           then as a statement if the first approach fails.

           Utility function to accept strings in functions that otherwise
           expect code objects
        """
        try:
            c = compile(source, name, 'eval')
        except SyntaxError:
            c = compile(source, name, 'exec')
        return c

    def findlinestarts(code):
        """Find the offsets in a byte code which are start of lines in the source.

        Generate pairs (offset, lineno) as described in Python/compile.c.

        """
        from xoutil.eight import zip
        byte_increments = [_ord(x) for x in code.co_lnotab[0::2]]
        line_increments = [_ord(x) for x in code.co_lnotab[1::2]]

        lastlineno = None
        lineno = code.co_firstlineno
        addr = 0
        for byte_incr, line_incr in zip(byte_increments, line_increments):
            if byte_incr:
                if lineno != lastlineno:
                    yield (addr, lineno)
                    lastlineno = lineno
                addr += byte_incr
            lineno += line_incr
        if lineno != lastlineno:
            yield (addr, lineno)

    def _get_instructions_bytes(code, varnames=None, names=None,
                                constants=None, cells=None, linestarts=None,
                                line_offset=0):
        """Iterate over the instructions in a bytecode string.

        Generates a sequence of Instruction namedtuples giving the details of
        each opcode.  Additional information about the code's runtime
        environment (e.g. variable names, constants) can be specified using
        optional arguments.

        """
        from dis import HAVE_ARGUMENT, EXTENDED_ARG
        from dis import hasconst, hasname
        from dis import hasjrel, haslocal, hascompare, hasfree
        from dis import opname, cmp_op
        hasnargs = []   # No in Python 2
        labels = findlabels(code)
        extended_arg = 0
        starts_line = None
        # enumerate() is not an option, since we sometimes process
        # multiple elements on a single pass through the loop
        n = len(code)
        i = 0
        while i < n:
            op = _ord(code[i])
            offset = i
            if linestarts is not None:
                starts_line = linestarts.get(i, None)
                if starts_line is not None:
                    starts_line += line_offset
            is_jump_target = i in labels
            i = i+1
            arg = None
            argval = None
            argrepr = ''
            if op >= HAVE_ARGUMENT:
                arg = _ord(code[i]) + _ord(code[i+1])*256 + extended_arg
                extended_arg = 0
                i = i+2
                if op == EXTENDED_ARG:
                    extended_arg = arg*65536
                #  Set argval to the dereferenced value of the argument when
                #  availabe, and argrepr to the string representation of
                #  argval.  _disassemble_bytes needs the string repr of the
                #  raw name index for LOAD_GLOBAL, LOAD_CONST, etc.
                argval = arg
                if op in hasconst:
                    argval, argrepr = _get_const_info(arg, constants)
                elif op in hasname:
                    argval, argrepr = _get_name_info(arg, names)
                elif op in hasjrel:
                    argval = i + arg
                    argrepr = "to " + repr(argval)
                elif op in haslocal:
                    argval, argrepr = _get_name_info(arg, varnames)
                elif op in hascompare:
                    argval = cmp_op[arg]
                    argrepr = argval
                elif op in hasfree:
                    argval, argrepr = _get_name_info(arg, cells)
                elif op in hasnargs:
                    argrepr = "%d positional, %d keyword pair" % (
                        _ord(code[i-2]), _ord(code[i-1]))
            yield Instruction(opname[op], op,
                              arg, argval, argrepr,
                              offset, starts_line, is_jump_target)

    def findlabels(code):
        """Detect all offsets in a byte code which are jump targets.

        Return the list of offsets.

        """
        from dis import HAVE_ARGUMENT, hasjrel, hasjabs
        labels = []
        # enumerate() is not an option, since we sometimes process
        # multiple elements on a single pass through the loop
        n = len(code)
        i = 0
        while i < n:
            op = _ord(code[i])
            i = i+1
            if op >= HAVE_ARGUMENT:
                arg = _ord(code[i]) + _ord(code[i+1])*256
                i = i+2
                label = -1
                if op in hasjrel:
                    label = i+arg
                elif op in hasjabs:
                    label = arg
                if label >= 0:
                    if label not in labels:
                        labels.append(label)
        return labels

    def _get_const_info(const_index, const_list):
        """Helper to get optional details about const references

           Returns the dereferenced constant and its repr if the constant
           list is defined.
           Otherwise returns the constant index and its repr().
        """
        argval = const_index
        if const_list is not None:
            argval = const_list[const_index]
        return argval, repr(argval)

    def _get_name_info(name_index, name_list):
        """Helper to get optional details about named references

           Returns the dereferenced name as both value and repr if the name
           list is defined.
           Otherwise returns the name index and its repr().
        """
        argval = name_index
        if name_list is not None:
            argval = name_list[name_index]
            argrepr = argval
        else:
            argrepr = repr(argval)
        return argval, argrepr

    from xoutil import collections

    _Instruction = collections.namedtuple(
        "_Instruction",
        "opname opcode arg argval argrepr offset starts_line is_jump_target"
    )

    class Instruction(_Instruction):
        """Details for a bytecode operation

           Defined fields:
             opname - human readable name for operation
             opcode - numeric code for operation
             arg - numeric argument to operation (if any), otherwise None
             argval - resolved arg value (if known), otherwise same as arg
             argrepr - human readable description of operation argument
             offset - start index of operation within bytecode sequence
             starts_line - line started by this opcode (if any), otherwise None
             is_jump_target - True if other code jumps to here, otherwise False
        """

        def _disassemble(self, lineno_width=3, mark_as_current=False):
            """Format instruction details for inclusion in disassembly output

            *lineno_width* sets the width of the line number field (0 omits it)
            *mark_as_current* inserts a '-->' marker arrow as part of the line
            """
            fields = []
            # Column: Source code line number
            if lineno_width:
                if self.starts_line is not None:
                    lineno_fmt = "%%%dd" % lineno_width
                    fields.append(lineno_fmt % self.starts_line)
                else:
                    fields.append(' ' * lineno_width)
            # Column: Current instruction indicator
            if mark_as_current:
                fields.append('-->')
            else:
                fields.append('   ')
            # Column: Jump target marker
            if self.is_jump_target:
                fields.append('>>')
            else:
                fields.append('  ')
            # Column: Instruction offset from start of code sequence
            fields.append(repr(self.offset).rjust(4))
            # Column: Opcode name
            fields.append(self.opname.ljust(20))
            # Column: Opcode argument
            if self.arg is not None:
                fields.append(repr(self.arg).rjust(5))
                # Column: Opcode argument details
                if self.argrepr:
                    fields.append('(' + self.argrepr + ')')
            return ' '.join(fields).rstrip()

    def _format_code_info(co):
        lines = []
        lines.append("Name:              %s" % co.co_name)
        lines.append("Filename:          %s" % co.co_filename)
        lines.append("Argument count:    %s" % co.co_argcount)
        if hasattr(co, 'co_kwonlyargcount'):
            lines.append("Kw-only arguments: %s" % co.co_kwonlyargcount)
        lines.append("Number of locals:  %s" % co.co_nlocals)
        lines.append("Stack size:        %s" % co.co_stacksize)
        lines.append("Flags:             %s" % pretty_flags(co.co_flags))
        if co.co_consts:
            lines.append("Constants:")
            for i_c in enumerate(co.co_consts):
                lines.append("%4d: %r" % i_c)
        if co.co_names:
            lines.append("Names:")
            for i_n in enumerate(co.co_names):
                lines.append("%4d: %s" % i_n)
        if co.co_varnames:
            lines.append("Variable names:")
            for i_n in enumerate(co.co_varnames):
                lines.append("%4d: %s" % i_n)
        if co.co_freevars:
            lines.append("Free variables:")
            for i_n in enumerate(co.co_freevars):
                lines.append("%4d: %s" % i_n)
        if co.co_cellvars:
            lines.append("Cell variables:")
            for i_n in enumerate(co.co_cellvars):
                lines.append("%4d: %s" % i_n)
        return "\n".join(lines)

    COMPILER_FLAG_NAMES = {   # noqa
        0x0001: "OPTIMIZED",
        0x0002: "NEWLOCALS",
        0x0004: "VARARGS",
        0x0008: "VARKEYWORDS",
        0x0010: "NESTED",
        0x0020: "GENERATOR",

        # The CO_NOFREE flag is set if there are no free or cell variables.
        # This information is redundant, but it allows a single flag test
        # to determine whether there is any extra work to be done when the
        # call frame it setup.
        0x0040: "NOFREE",

        # Python 3.5.  We don't support them but they're for completion and
        # possible work
        0x0080: "COROUTINE",
        0x0100: "ITERABLE_COROUTINE",

        0x1000: "GENERATOR_ALLOWED",  # no used anymore

        # Python 3 does not use the following
        0x2000: "FUTURE_DIVISION",
        0x4000: "FUTURE_ABSOLUTE_IMPORT",
        0x8000: "FUTURE_WITH_STATEMENT",

        0x10000: "FUTURE_PRINT_FUNCTION",
        0x20000: "FUTURE_UNICODE_LITERALS",
    }

    def pretty_flags(flags):
        """Return pretty representation of code flags."""
        names = []
        for i in range(32):
            flag = 1 << i
            if flags & flag:
                names.append(COMPILER_FLAG_NAMES.get(flag, hex(flag)))
                flags ^= flag
                if not flags:
                    break
        else:
            names.append(hex(flags))
        return ", ".join(names)

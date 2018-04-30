#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------
# Copyright (c) Merchise Autrement [~º/~] and Contributors
# All rights reserved.
#

#  Copyright (c) 1999 John Aycock
#  Copyright (c) 2000-2002 by hartmut Goebel <h.goebel@crazy-compilers.com>
#  Copyright (c) 2005 by Dan Pascu <dan@windowmaker.org>
#
#  See main module for license.
#

# flake8: noqa

__all__ = ['Token', 'Scanner', 'getscanner']

import types
import dis
from array import array
from sys import intern  # Py3k

# Py3.5 changes BUILD_MAP, adds BUILD_MAP_UNPACK, BUILD_MAP_UNPACK_WITH_CALL
from .eight import pypy as _pypy, _py_version, override
from .exceptions import ScannerError, ScannerAssertionError  # noqa
from .tools import PACKOPARG


HAVE_ARGUMENT = dis.HAVE_ARGUMENT

# This fills the module's global with all the byte-code opnames, NOP,
# BUILD_LIST, etc, will be defined.  This confuses flycheck and other tools
# but we'll stick to this.
globals().update(
    {k.replace('+', '_'): v for (k, v) in list(dis.opmap.items())}
)

if not _pypy:
    BUILD_LIST_FROM_ARG = None

JUMP_IF_OR_POPs = (JUMP_IF_TRUE_OR_POP, JUMP_IF_FALSE_OR_POP)  # noqa
POP_JUMP_IFs = (POP_JUMP_IF_TRUE, POP_JUMP_IF_FALSE)  # noqa
CONDITIONAL_JUMPs = JUMP_IF_OR_POPs + POP_JUMP_IFs
UNCONDITIONAL_JUMPs = (JUMP_ABSOLUTE, JUMP_FORWARD)  # noqa
RELATIVE_JUMPs = (FOR_ITER, JUMP_FORWARD)   # noqa
ABSOLUTE_JUMPs = (JUMP_ABSOLUTE, ) + CONDITIONAL_JUMPs


ANY_JUMPs = RELATIVE_JUMPs + ABSOLUTE_JUMPs


def jumps_on_true(x):
    return x in (JUMP_IF_TRUE_OR_POP, POP_JUMP_IF_TRUE)


def jumps_on_false(x):
    return x in (JUMP_IF_FALSE_OR_POP, POP_JUMP_IF_FALSE)


def ensure_symbols(*syms, default=None):
    'Ensure symbols are in the module\'s globals with value default'
    gl = globals()
    for sym in syms:
        gl.setdefault(sym, default)


# Missing in Py3.6:
ensure_symbols('CALL_FUNCTION_VAR', 'CALL_FUNCTION_VAR_KW', )


# New in Python  3.6
ensure_symbols('CALL_FUNCTION_EX', 'BUILD_CONST_KEY_MAP',
               'BUILD_TUPLE_UNPACK_WITH_CALL', 'BUILD_CONST_KEY_MAP',
               'BUILD_STRING', 'STORE_ANNOTATION', 'FORMAT_VALUE')


# The byte-codes that need to be customized cause they take a variable
# number of stack objects.
CUSTOMIZABLE = (
    BUILD_TUPLE_UNPACK,
    BUILD_LIST_UNPACK,
    BUILD_SET_UNPACK,
    BUILD_MAP_UNPACK,
    BUILD_MAP_UNPACK_WITH_CALL,
    BUILD_TUPLE_UNPACK_WITH_CALL,
    BUILD_MAP,
    BUILD_LIST,
    BUILD_TUPLE,
    BUILD_SET,
    BUILD_SLICE,
    BUILD_CONST_KEY_MAP,
    UNPACK_SEQUENCE,
    MAKE_FUNCTION,
    CALL_FUNCTION,
    CALL_FUNCTION_VAR,
    CALL_FUNCTION_KW,
    CALL_FUNCTION_VAR_KW,
    CALL_FUNCTION_EX,
    RAISE_VARARGS,
    BUILD_STRING,
)


from contextlib import contextmanager
from dis import Bytecode, Instruction as BaseInstruction


class label:
    '''Represent a named label in a instruction set building process.

    See `InstructionSetBuilder`:class: for details.

    When used as keys in dictionaries, labels and string are
    indistinguishable::

       >>> ls = {}
       >>> ls['label1'] = 1
       >>> ls[label('label1')] = 2

       >>> ls
       {'label1': 2}

       >>> ls[label('label2')] = 3
       >>> ls['label2'] = 4

       >>> ls
       {<label: label2>: 4, 'label1': 2}

    '''
    def __init__(self, which):
        if isinstance(which, label):
            name = which.name
        else:
            name = which
        self.name = name

    def __eq__(self, other):
        if isinstance(other, label):
            return self.name == other.name
        else:
            return self.name == other

    def __hash__(self):
        return hash(self.name)

    def __repr__(self):
        return '<label: %s>' % self.name


class InstructionSetBuilder:
    '''A helper to build a set of instructions.

    Usage::

        builder = InstructionSetBuilder()
        with builder() as Instruction:
            Instruction(opcode='LOAD_NAME', arg=0, argval='x')

    Features:

    - Keeps the offsets.

    - Allows to set `named labels <label>`:class: as the arg of relative and
      absolute jumps.

    - Calculates jump targets.

    '''
    def __init__(self):
        self.reset()

    def reset(self):
        self.offset = 0
        self.instructions = []
        self.labels = {}

    @contextmanager
    def __call__(self):
        self.reset()

        def build(**kwargs):
            labelname = kwargs.pop('label', None)
            offset = kwargs.pop('offset', self.offset)
            kwargs['offset'] = offset
            result = Instruction(**kwargs)
            self.offset += result.size
            if labelname:
                self.labels[label(labelname)] = len(self.instructions)
            self.instructions.append(result)
            return result

        yield build

    def __iter__(self):
        self._resolve()
        return iter(self.instructions)

    @property
    def code(self):
        '''Return the byte-code for the current set of instructions.'''
        res = array('B')
        for i in self:
            res.frombytes(i.code)
        tobytes = getattr(res, 'tobytes', res.tostring)
        return tobytes()

    @property
    def current_instruction_set(self):
        return list(self)

    def _resolve(self):
        instrs = self.instructions
        targets = []
        for instr in instrs:
            if instr.opcode in dis.hasjabs and isinstance(instr.arg, label):
                arg = instr.arg = instrs[self.labels[instr.arg]].offset
                instr.argval = arg
                instr.argrepr = ''
                targets.append(arg)
            elif instr.opcode in dis.hasjrel and isinstance(instr.arg, label):
                target = instrs[self.labels[instr.arg]]
                instr.arg = arg = target.offset - instr.size - instr.offset
                instr.argval = target.offset
                instr.argrepr = 'to %d' % target.offset
                targets.append(target)
            elif instr.opcode in dis.hasjrel or instr.opcode in dis.hasjabs:
                targets.append(instr.target)
        for instr in instrs:
            instr.is_jump_target = instr.offset in targets


class Instruction:
    def __init__(self, *args, **kwargs):
        if args and len(args) > 1 or kwargs:
            opname = kwargs.get('opname', None)
            opcode = kwargs.get('opcode', None)
            assert opname or opcode
            if opname and not opcode:
                opcode = dis.opmap[opname]
            elif opcode and not opname:
                opname = dis.opname[opcode]
            kwargs['opname'] = opname
            kwargs['opcode'] = opcode
            kwargs.setdefault('arg', None)
            kwargs.setdefault('argval', kwargs['arg'])
            kwargs.setdefault('argrepr',
                              repr(kwargs['arg']) if kwargs['arg'] else '')
            kwargs.setdefault('starts_line', None)
            kwargs.setdefault('is_jump_target', False)  # To be resolved
            instruction = BaseInstruction(*args, **kwargs)
        elif args and len(args) == 1:
            which = args[0]
            if isinstance(which, (Instruction, BaseInstruction)):
                instruction = BaseInstruction(*tuple(which))
            else:
                raise TypeError('Invalid arguments for Instruction')
        else:
            raise TypeError('Instruction requires arguments')
        self.__dict__.update({
            field: getattr(instruction, field)
            for field in BaseInstruction._fields
        })

    @property
    def target(self):
        opcode = self.opcode
        if opcode in dis.hasjrel:
            assert self.argval == self.arg + self.size + self.offset, \
                '%s != %s + %s + %s' % (self.argval, self.arg, self.size,
                                        self.offset)
            return self.argval
        else:
            assert opcode in dis.hasjabs
            return self.argval

    @override(_py_version < (3, 6))
    def _get_code(self):
        if self.opcode >= dis.HAVE_ARGUMENT:
            arg = self.arg
            bytes_ = []
            extended = arg >> 16
            if extended:
                bytes_ = [dis.EXTENDED_ARG, extended & 0xFF, extended >> 8]
            else:
                bytes_ = []
            bytes_.extend([self.opcode, arg & 0xFF, arg >> 8])
        else:
            bytes_ = [self.opcode]
        res = array('B')
        res.extend(bytes_)
        tobytes = getattr(res, 'tobytes', res.tostring)
        return tobytes()

    @_get_code.override((3, 6) <= _py_version)
    def _get_code(self):
        if self.opcode >= dis.HAVE_ARGUMENT:
            arg = self.arg
        else:
            arg = 0
        bytes_ = []
        # extended = arg >> 16
        # if extended:
        #     bytes_ = [dis.EXTENDED_ARG, extended & 0xFF, extended >> 8]
        # else:
        #     bytes_ = []
        bytes_.append(PACKOPARG(self.opcode, arg))
        res = array('H')
        res.extend(bytes_)
        tobytes = getattr(res, 'tobytes', res.tostring)
        return tobytes()

    @property
    def code(self):
        '''Return the code string for this instruction.

        .. note:: If the opcode contains an argument which is bigger than the
           available two bytes, the opcode will be prepended by an
           EXTENDED_ARG.

        '''
        return self._get_code()

    @property
    def size(self):
        import dis
        if _py_version < (3, 6):
            return 1 if self.opcode < dis.HAVE_ARGUMENT else 3
        else:
            # versionchanged:: 3.6
            #
            # Use 2 bytes for each instruction. Previously the number of bytes
            # varied by instruction.
            return 2

    @property
    def _instruction(self):
        return BaseInstruction(*tuple(self))

    def _asdict(self):
        from xoutil.future.collections import OrderedDict
        return OrderedDict([
            (field, getattr(self, field))
            for field in BaseInstruction._fields
        ])

    def __iter__(self):
        return iter(self._asdict().values())

    def __repr__(self):
        return repr(self._instruction)

    __hash__ = None   # we're are mutable, not suitable for keys.

    def __eq__(self, other):
        from xoutil.objects import validate_attrs
        return validate_attrs(self, other,
                              force_equals=BaseInstruction._fields)


class Token:
    """Class representing a byte-code token.

    A byte-code token is equivalent to the contents of one line
    as output by dis.dis().

    """
    def __init__(self, name, arg=None, argval=None, argrepr=None,
                 offset=-1, starts_line=False, instruction=None):
        self.name = intern(str(name))
        self.arg = arg
        self.argval = argval
        self.argrepr = argrepr or repr(argval)
        self.offset = offset
        self.starts_line = starts_line
        if instruction:
            self.is_jump_target = instruction.is_jump_target
        else:
            self.is_jump_target = False
        self.instruction = instruction

    @classmethod
    def from_instruction(cls, instruction):
        return cls(
            instruction.opname,
            arg=instruction.arg,
            argval=instruction.argval,
            argrepr=instruction.argrepr,
            offset=instruction.offset,
            starts_line=instruction.starts_line,
            instruction=instruction
        )

    @property
    def type(self):
        # Several parts of the parser and walker assume a type attribute.
        # This is consistent with the type attribute for rules.
        return self.name

    __hash__ = None

    def __len__(self):
        return 0

    def __bool__(self):
        return True
    __nonzero__ = __bool__

    def __eq__(self, other):
        if isinstance(other, Token):
            # both are tokens: compare type and pattr
            return self.name == other.name and self.argval == other.argval
        else:
            return self.name == other

    def __repr__(self):
        return '<%s(%s, %s): %s>' % (
            str(self.name), self.arg, self.argval, self.offset
        )

    def __str__(self):
        argval = self.argval
        if self.starts_line:
            return '\n%s\t%-17s %r' % (self.offset, self.name, argval)
        else:
            return '%s\t%-17s %r' % (self.offset, self.name, argval)

    def __hash__(self):
        return hash(self.name)

    def __getitem__(self, i):
        raise IndexError


class Code:
    """Class for representing code-objects.

    This is similar to the original code object, but additionally
    the diassembled code is stored in the attribute '_tokens'.

    """
    def __init__(self, co, scanner, classname=None):
        for i in dir(co):
            if i.startswith('co_'):
                setattr(self, i, getattr(co, i))
        self._tokens, self._customize = scanner.disassemble(co, classname)


class Structure:
    def __init__(self, start, end, type_):
        self.start = start
        self.end = end
        self.type = type_

    def __repr__(self):
        return '{{{start}, {end}, {type}}}'.format(**self.__dict__)

    def restrict(self, target):
        """Return the target within the parent structure boundaries.

        If `target` is not completely contained within the parent
        boundaries, return the end of the of the parent.  Otherwise,
        return `target`.

        """
        if self.start < target < self.end:
            return target
        else:
            return self.end


class Scanner:
    def __init__(self, version, Token=Token):
        self.version = version
        from sys import version_info
        self.pyversion = float('%d.%d' % version_info[0:2])
        self.showasm = False
        self.out = None
        self.setTokenClass(Token)
        self.JUMP_OPs = [dis.opname[op] for op in dis.hasjrel + dis.hasjabs]

    def setShowAsm(self, showasm, out=None):
        self.showasm = showasm
        self.out = out

    def setTokenClass(self, tokenClass=Token):
        assert type(tokenClass) == type
        self.Token = tokenClass

    def resetTokenClass(self):
        self.setTokenClass()

    def disassemble(self, co, normalize=True):
        'Produce the tokens for the code.'
        if normalize is True:
            normalize = keep_single_return
        elif normalize is False:
            normalize = lambda x: x
        else:
            from xoutil.fp.tools import compose
            normalize = compose(*normalize)
        result = []
        customizations = {}
        # The 'jumps' is filled by the `detect_structure` closure function
        # below.  It maps the offset of jumping instructions to the farthest
        # offset within the instruction 'structure'.  This allows to keep
        # track of nested boolean and conditional expressions.  The structures
        # are simply the span of instructions pertaining a single (outer)
        # expression.  Some optimization steps make jumps outside the outer
        # structures, jumps keep the right 'target' for those.
        #
        # Nested conditional are problematic since they may RETURN at any
        # moment.
        jumps = {}
        BOOLSTRUCT = 'and/or'  # mark for nested conditionals
        structures = []

        def get_instruction_at(offset, instructions):
            return next(i for i in enumerate(instructions)
                        if i[-1].offset == offset)

        def get_parent_structure(offset):
            '''Return the minimal structure the given `offset` lies into.

            Since structures don't overlap unless fully contained they form a
            nested structure.  Minimal means there's no an inner structure
            which contains the given `offset`.

            An offset at the very end of a structure is part of the parent
            structure.  An offset at the start of a structure is part of it.

            In the diagram shown below dots are offsets, delimiter show the
            start and end of structures.

            ::

                1     2        3       4                5
                [     (    )   (       {       }   )    (  )]
                .............................................
                      ^            ^       ^   ^
                      At 2         |       |   Not at 4
                                   At 3    |
                                           At 4

            '''
            parent = structures[0]
            for struct in structures[1:]:
                start = struct.start
                end = struct.end
                if parent.start <= start <= offset < end <= parent.end:
                    parent = struct
            return parent

        def detect_structure(instruction, index, instructions):
            parent = get_parent_structure(instruction.offset)
            offset = instruction.offset
            next_offset = offset + instruction.size
            if instruction.opcode in POP_JUMP_IFs:
                target = instruction.target
                target_index, target_inst = get_instruction_at(target, instructions)
                restricted = parent.restrict(target)
                if target != restricted and parent.type == BOOLSTRUCT:
                    # The target is not within the parent boundaries, this is
                    # most likely an "out the loop" jump.
                    #
                    # The jumps map needs to be set from the current to the
                    # last offset of the structure! This way we won't go
                    # farther than we should.
                    jumps[offset] = restricted
                    return
                above_target = instructions[target_index-1]
                above_opcode = above_target.opcode
                above_is_condjump = above_opcode in CONDITIONAL_JUMPs
                above_is_retval = above_target == RETURN_VALUE
                if target > offset and above_is_condjump or above_is_retval:
                    # The instruction above the target is a conditional jump
                    # or a RETURN_VALUE, this a likely a nested conditional.
                    #
                    # The jumps maps need to be to the instruction above the
                    # target and a new structure is created spanning from the
                    # next instruction to the instruction above the target.
                    jumps[offset] = end = instructions[target_index-1].offset
                    structures.append(Structure(next_offset, end, BOOLSTRUCT))
                    return
            elif instruction.opcode in JUMP_IF_OR_POPs:
                target = instruction.target
                restricted = parent.restrict(target)
                jumps[offset] = restricted

        def find_jump_targets(instructions):
            '''Find all targets of jumps.

            '''
            last = instructions[-1].offset + instructions[-1].size
            structures[:] = [Structure(0, last, 'root')]  # The whole program
            result = {}
            for index, instruction in enumerate(instructions):
                detect_structure(instruction, index, instructions)
                opcode = instruction.opcode
                offset = instruction.offset
                size = instruction.size
                argval = instruction.argval
                if opcode >= dis.HAVE_ARGUMENT:
                    label = jumps.get(instruction.offset)
                    if label is None:
                        if opcode == JUMP_FORWARD:
                            label = argval
                    if label is not None and label != -1:
                        result.setdefault(label, []).append(offset)
            return result

        def emit(instruction):
            result.append(instruction)

        def emit_const(instruction):
            if instruction.opcode not in dis.hasconst:
                raise ScannerError(
                    "byte-code '%s' has no const" % instruction.opname
                )
            const = instruction.argval
            opname = instruction.opname
            if isinstance(const, types.CodeType):
                if const.co_name == '<lambda>':
                    assert instruction.opname == 'LOAD_CONST'   # XXX Needed?
                    opname = 'LOAD_LAMBDA'
                elif const.co_name == '<genexpr>':
                    opname = 'LOAD_GENEXPR'
                elif const.co_name == '<dictcomp>':
                    opname = 'LOAD_DICTCOMP'
                elif const.co_name == '<setcomp>':
                    opname = 'LOAD_SETCOMP'
                elif const.co_name == '<listcomp>':
                    opname = 'LOAD_LISTCOMP'
            res = Instruction(instruction)
            res.opname = opname
            return emit(res)

        def emit_come_from(offset, target, index):
            emit(Token('COME_FROM',
                       arg=target,
                       argval=target,
                       argrepr='from %s' % j,
                       offset="%s_%d" %
                       (offset, index)))

        def customize(instruction, arg=None):
            opname = instruction.opname
            if arg is None:
                arg = instruction.arg
            opname = '%s_%d' % (opname, arg)
            customizations[opname] = arg
            instruction.opname = opname

        instructions = list(normalize(Instruction(i) for i in Bytecode(co)))
        targets = find_jump_targets(instructions)
        for index, instruction in enumerate(instructions):
            opcode = instruction.opcode
            offset = instruction.offset
            _jumps = targets.get(offset, [])
            for k, j in enumerate(_jumps):
                emit_come_from(offset, j, k)
            if opcode in CUSTOMIZABLE:
                customize(instruction)
            if opcode == FORMAT_VALUE:
                # See the documentation of `dis.FORMAT_VALUE`
                flags = instruction.arg
                has_spec = flags & 0x04 == 0x04
                if has_spec:
                    instruction.opname += '_WITH_SPEC'
            if opcode == JUMP_ABSOLUTE:  # noqa
                if instruction.argval < instruction.offset:
                    # Make JUMP_ABSOLUTE to a previous offset a JUMP_BACK.
                    # The parser relies on this virtual code to recognize the
                    # comprehension loop.
                    instruction.opname = 'JUMP_BACK'
            if opcode == EXTENDED_ARG:   # noqa
                pass   # don't emit
            elif opcode in dis.hasconst:
                emit_const(instruction)
            else:
                emit(instruction)

        tokens = [
            Token.from_instruction(i) if not isinstance(i, Token) else i
            for i in result
        ]
        return tokens, customizations

    def detect_structure(self, pos, op=None, structs=None):
        """Detect structures and their boundaries to fix optimized jumps in Python
        2.3+

        TODO:  What are structures and their boundaries?

        """
        # TODO: check the struct boundaries more precisely -Dan
        code = self.code
        if not structs:
            structs = self.structs
        # Ev remove this test and make op a mandatory argument -Dan
        if op is None:
            op = code[pos]
        parent = self.get_parent_structure(offset=pos)
        if op in POP_JUMP_IFs:
            start = pos+3
            target = self.get_target(pos, op)
            rtarget = self.restrict_to_parent(target, parent)
            pre = self.prev
            # If the target is not within the parents struct this is most
            # likely a "out of the loop" jump: a fixed jump.
            if target != rtarget and parent['type'] == 'and/or':
                self.fixed_jumps[pos] = rtarget
                return
            # does this jump to right after another cond jump?
            # if so, it's part of a larger conditional
            if (code[pre[target]] in CONDITIONAL_JUMPs) and (target > pos):
                self.fixed_jumps[pos] = pre[target]
                structs.append({'type': 'and/or',
                                'start': start,
                                'end': pre[target]})
                return
            # is this an `if and`
            if op == POP_JUMP_IF_FALSE:
                match = self.rem_or(start,
                                    self.next_stmt[pos],
                                    POP_JUMP_IF_FALSE,
                                    target)
                match = self.remove_mid_line_ifs(match)
                if match:
                    if code[pre[rtarget]] in UNCONDITIONAL_JUMPs \
                            and pre[rtarget] not in self.stmts \
                            and self.restrict_to_parent(self.get_target(pre[rtarget]), parent) == rtarget:  # noqa
                        if code[pre[pre[rtarget]]] == JUMP_ABSOLUTE \
                                and self.remove_mid_line_ifs([pos]) \
                                and target == self.get_target(pre[pre[rtarget]]) \
                                and (pre[pre[rtarget]] not in self.stmts or self.get_target(pre[pre[rtarget]]) > pre[pre[rtarget]])\
                                and 1 == len(self.remove_mid_line_ifs(self.rem_or(start, pre[pre[rtarget]], POP_JUMP_IFs, target))):
                            pass
                        elif code[pre[pre[rtarget]]] == RETURN_VALUE \
                                and self.remove_mid_line_ifs([pos]) \
                                and 1 == (len(set(self.remove_mid_line_ifs(self.rem_or(start, pre[pre[rtarget]],
                                                             POP_JUMP_IFs, target))) \
                                              | set(self.remove_mid_line_ifs(self.rem_or(start, pre[pre[rtarget]],
                                                                                         POP_JUMP_IFs + (JUMP_ABSOLUTE, ), pre[rtarget], True))))):
                            pass
                        else:
                            fix = None
                            jump_ifs = self.all_instr(start, self.next_stmt[pos], POP_JUMP_IF_FALSE)
                            last_jump_good = True
                            for j in jump_ifs:
                                if target == self.get_target(j):
                                    if self.lines[j].next == j+3 and last_jump_good:
                                        fix = j
                                        break
                                else:
                                    last_jump_good = False
                            self.fixed_jumps[pos] = fix or match[-1]
                            return
                    else:
                        self.fixed_jumps[pos] = match[-1]
                        return
            else:  # op == POP_JUMP_IF_TRUE
                next = self.next_stmt[pos]
                if pre[next] == pos:
                    pass
                elif code[next] in UNCONDITIONAL_JUMPs and target == self.get_target(next):
                    if code[pre[next]] == POP_JUMP_IF_FALSE:
                        if code[next] == JUMP_FORWARD or target != rtarget or code[pre[pre[rtarget]]] not in UNCONDITIONAL_JUMPs:
                            self.fixed_jumps[pos] = pre[next]
                            return
                elif code[next] == JUMP_ABSOLUTE and code[target] in UNCONDITIONAL_JUMPs:
                    next_target = self.get_target(next)
                    if self.get_target(target) == next_target:
                        self.fixed_jumps[pos] = pre[next]
                        return
                    elif code[next_target] in UNCONDITIONAL_JUMPs and self.get_target(next_target) == self.get_target(target):
                        self.fixed_jumps[pos] = pre[next]
                        return
            # don't add a struct for a while test, it's already taken care of
            if pos in self.ignore_if:
                return

            if code[pre[rtarget]] == JUMP_ABSOLUTE and pre[rtarget] in self.stmts \
                    and pre[rtarget] != pos and pre[pre[rtarget]] != pos:
                if code[rtarget] == JUMP_ABSOLUTE and code[rtarget+3] == POP_BLOCK:
                    if code[pre[pre[rtarget]]] != JUMP_ABSOLUTE:
                        pass
                    elif self.get_target(pre[pre[rtarget]]) != target:
                        pass
                    else:
                        rtarget = pre[rtarget]
                else:
                    rtarget = pre[rtarget]
            # does the if jump just beyond a jump op, then this is probably an
            # if statement
            if code[pre[rtarget]] in UNCONDITIONAL_JUMPs:
                if_end = self.get_target(pre[rtarget])
                # is this a loop not an if?
                if if_end < pre[rtarget] and code[pre[if_end]] == SETUP_LOOP:
                    if if_end > start:
                        return
                end = self.restrict_to_parent(if_end, parent)
                structs.append({'type': 'if-then',
                                'start': start,
                                'end': pre[rtarget]})
                self.not_continue.add(pre[rtarget])
                if rtarget < end:
                    structs.append({'type': 'if-else',
                                    'start': rtarget,
                                    'end': end})
            elif code[pre[rtarget]] == RETURN_VALUE:
                structs.append({'type': 'if-then',
                                'start': start,
                                'end': rtarget})
                self.return_end_ifs.add(pre[rtarget])
        elif op in JUMP_IF_OR_POPs:
            target = self.get_target(pos, op)
            self.fixed_jumps[pos] = self.restrict_to_parent(target, parent)


# A cache from version to Scanners.
# Since Scanners are not thread-safe the getscanner accepts a
# get_current_thread argument so that scanners don't cross threads.
__scanners = {}


try:
    from thread import get_ident
except ImportError:
    from _thread import get_ident


def getscanner(version=None, get_current_thread=get_ident):
    from xoutil.symbols import Unset
    if not version:
        from sys import version_info
        version = '.'.join(str(component) for component in version_info[:2])
    key = (version, get_current_thread())
    result = __scanners.get(key, Unset)
    if result is Unset:
        __scanners[key] = result = Scanner(version)
    return result


def without_nops(instructions):
    '''Return the same instruction set with NOPs removed.

    The jump targets are properly updated.

    Loosely based on the same algorithm in `Python/peephole.c`.

    :param instructions:  An iterable of `instructions <Instruction>`:class:.

    :return: A generator of instructions.

    '''
    # Builds a map from current offset to offsets discounting NOPs.
    addrmap = []
    nops = 0
    instructions = list(instructions)   # Consume the iterator once.
    for i in instructions:
        addrmap[i.offset:i.offset + i.size] = list(range(i.offset - nops, i.offset + i.size - nops))
        if i.opcode == NOP:
            nops += 1
    args = []
    offset = 0
    targets = []
    for i in instructions:
        vals = dict(i._asdict())
        vals['offset'] = offset
        if i.opcode in dis.hasjabs:
            vals['arg'] = vals['argval'] = target = addrmap[i.arg]
            targets.append(target)
        elif i.opcode in dis.hasjrel:
            offset = i.offset
            size = i.size
            target = offset + i.arg + size
            newoffset = addrmap[offset]
            newtarget = addrmap[target]
            targets.append(newtarget)
            vals['arg'] = vals['argval'] = newtarget - newoffset - size
        if i.opcode != NOP:
            args.append(vals)
            offset += i.size
    # Unfortunately we need a third pass to adjust the is_jump_target
    for vals in args:
        offset = vals['offset']
        vals['is_jump_target'] = offset in targets
        yield Instruction(**vals)


def keep_single_return(instructions):
    '''Transform the instructions so the a single RETURN_VALUE is kept at the
    bottom.

    If the original `instructions` don't have a RETURN_VALUE at the very end,
    return the same instructions set.

    Otherwise all but the last RETURN_VALUE will be replaced by a JUMP_FORWARD
    that targets the RETURN_VALUE at the end of the instructions.

    Offsets and jump targets are updated.

    :param instructions: The original instructions.
    :type instructions: iterable

    :rtype: list

    '''
    instructions = list(instructions)
    last = instructions[-1]
    if last.opcode == RETURN_VALUE:
        builder = InstructionSetBuilder()
        lastlabel = label('previous-offset-%s' % last.offset)
        l = len(instructions) - 1  # noqa: E741
        with builder() as Instruction:
            for index, inst in enumerate(instructions):
                opname = inst.opname
                opcode = inst.opcode
                arg = inst.arg
                argval = inst.argval
                argrepr = inst.argrepr
                starts_line = inst.starts_line
                this = 'previous-offset-%s' % inst.offset
                if opcode == RETURN_VALUE:
                    if index != l:
                        # Don't replace the last RETURN_VALUE, but when doing
                        # it, make the jump go the last label.
                        opcode = JUMP_FORWARD
                        opname = 'JUMP_FORWARD'
                        arg = lastlabel
                elif opcode in ANY_JUMPs:
                    arg = label('previous-offset-%s' % inst.target)
                Instruction(label=this, opname=opname, opcode=opcode, arg=arg,
                            argval=argval, argrepr=argrepr,
                            starts_line=starts_line)
        return list(builder)
    else:
        return instructions


def normalize_pypy_conditional(instructions):
    '''Apply the pypy normalization rule.

    The pypy normalization rule states that:

      If the target of a ``JUMP_FORWARD`` (or ``JUMP_ABSOLUTE``) is a
      ``RETURN_VALUE`` replace the JUMP with the following instructions::

        RETURN_VALUE
        NOP
        NOP

    This rule does not only apply when using Pypy, the name simply comes
    because Pypy compiles conditional expressions using JUMPs.

    :param instructions:  An iterable of `instructions <Instruction>`:class:.

    :return: A generator of instructions.

    '''
    JUMP_ABS, JUMP_FWD = JUMP_ABSOLUTE, JUMP_FORWARD  # noqa
    RET = RETURN_VALUE  # noqa
    instructions = list(instructions)  # Consume an iterator only once.
    index = {i.offset: i for i in instructions}
    for i in instructions:
        fwdtarget = i.offset + i.arg + i.size if i.opcode == JUMP_FWD else None
        if i.opcode == JUMP_ABS and index[i.arg].opcode == RET \
           or i.opcode == JUMP_FWD and index[fwdtarget].opcode == RET:
            yield Instruction(opname='RETURN_VALUE', opcode=RET,
                              arg=None, argval=None, argrepr='',
                              offset=i.offset, starts_line=i.starts_line,
                              is_jump_target=i.is_jump_target)
            yield Instruction(opname='NOP', opcode=NOP, arg=None, argval=None,
                              argrepr='', offset=i.offset+1, starts_line=None,
                              is_jump_target=False)
            yield Instruction(opname='NOP', opcode=NOP, arg=None, argval=None,
                              argrepr='', offset=i.offset+2, starts_line=None,
                              is_jump_target=False)
        else:
            yield Instruction(i)


def xdis(f, native=False, normalize=True):
    '''Utility for quickly inspected the tokens produced by the scanner.

    :keyword native: Show only the tokens that match 'native' opcodes.
                     Virtual tokens are hidden and customizations regain their
                     original name.

    '''
    scanner = getscanner()
    tokens, customizations = scanner.disassemble(f, normalize=normalize)
    for token in tokens:
        if native and token.name in customizations:
            token.name, _ = token.name.rsplit('_', 1)
        if not native or token.name in dis.opname:
            _print_token(token)


def _print_token(token):
    lineno = token.starts_line
    offset = token.offset
    name = token.name
    argval = token.argval
    argrepr = token.argrepr
    istarget = token.is_jump_target
    print(' ', end='')   # pad
    print(str(lineno).ljust(3) if lineno else ' ' * 3, end=' ')
    print('>> ' if istarget else '   ', end='')
    print(str(offset).rjust(4), end=' ')
    print(str(name).ljust(20), end=' ')
    print(str(argval).ljust(4) if argval else ' ' * 4, end=' ')
    if argval:
        print('({})'.format(argrepr).ljust(6))
    else:
        print()


# Local Variables:
# fill-column: 150
# End:

# -*- encoding: utf-8 -*-
# ---------------------------------------------------------------------
# xotl.ql.revenge.scanners
# ---------------------------------------------------------------------
# Copyright (c) 2014, 2015 Merchise Autrement and Contributors
# All rights reserved.
#

#  Copyright (c) 1999 John Aycock
#  Copyright (c) 2000-2002 by hartmut Goebel <h.goebel@crazy-compilers.com>
#  Copyright (c) 2005 by Dan Pascu <dan@windowmaker.org>
#
#  See main module for license.
#

from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)

__all__ = ['Token', 'Scanner', 'getscanner']

import types
import dis
from collections import namedtuple
from array import array

#  We'll only support 2.7 and >=3.2,<3.5
from xoutil.eight import _py3, _py2, _pypy
from sys import version_info as _py_version
assert _py_version >= (2, 7, 0) and (
    not _py_version >= (3, 0) or (3, 2) <= _py_version < (3, 5))

# Py3.5 changes BUILD_MAP, adds BUILD_MAP_UNPACK, BUILD_MAP_UNPACK_WITH_CALL

try:
    from sys import intern  # Py3k
except ImportError:
    from __builtin__ import intern


from .exceptions import ScannerError, ScannerAssertionError  # noqa


HAVE_ARGUMENT = dis.HAVE_ARGUMENT

# This fills the module's global with all the byte-code opnames, NOP,
# BUILD_LIST, etc, will be defined.  This confuses flycheck and other tools
# but we'll stick to this.
globals().update(
    {k.replace('+', '_'): v for (k, v) in list(dis.opmap.items())}
)


if _py3:
    PRINT_ITEM = PRINT_ITEM_TO = PRINT_NEWLINE = PRINT_NEWLINE_TO = None
    STORE_SLICE_0 = STORE_SLICE_1 = STORE_SLICE_2 = STORE_SLICE_3 = None
    DELETE_SLICE_0 = DELETE_SLICE_1 = DELETE_SLICE_2 = DELETE_SLICE_3 = None
    EXEC_STMT = None
    DUP_TOPX = None

if _py2:
    DUP_TOP_TWO = None

if not _pypy:
    BUILD_LIST_FROM_ARG = None

del _py3, _py2, _pypy

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


# The byte-codes that need to be customized cause they take a variable
# number of stack objects.
CUSTOMIZABLE = (
    BUILD_LIST, BUILD_TUPLE, BUILD_SET, BUILD_SLICE,                  # noqa
    UNPACK_SEQUENCE, MAKE_FUNCTION, CALL_FUNCTION, MAKE_CLOSURE,      # noqa
    CALL_FUNCTION_VAR, CALL_FUNCTION_KW,                              # noqa
    CALL_FUNCTION_VAR_KW, DUP_TOPX, RAISE_VARARGS                     # noqa
)


# A virtual opcode that is not None
COME_FROM = object()


from contextlib import contextmanager
from .eight import Bytecode, Instruction as BaseInstruction


class label(object):
    '''Represent a named label in a instruction set building process.

    See `InstructionSetBuilder`:class: for details.

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


class InstructionSetBuilder(object):
    '''A helper to build a set of instructions.

    Usage::

        builder = InstructionSetBuilder()
        with builder() as Intruction:
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
        import array
        res = array.array('B')
        for i in self:
            res.fromstring(i.code)
        tobytes = getattr(res, 'tobytes', res.tostring)
        return tobytes()

    @property
    def current_instruction_set(self):
        return list(self)

    def _resolve(self):
        set = self.instructions
        targets = []
        for instr in set:
            if instr.opcode in dis.hasjabs and isinstance(instr.arg, label):
                arg = instr.arg = set[self.labels[instr.arg]].offset
                instr.argval = arg
                instr.argrepr = ''
                targets.append(arg)
            elif instr.opcode in dis.hasjabs:
                targets.append(instr.arg)
            elif instr.opcode in dis.hasjrel and isinstance(instr.arg, label):
                target = set[self.labels[instr.arg]].offset
                instr.arg = arg = target - 3 - instr.offset
                instr.argval = arg
                instr.argrepr = 'to %d' % target
                targets.append(target)
            elif instr.opcode in dis.hasjrel:
                targets.append(instr.arg + 3 + instr.offset)
        for instr in set:
            instr.is_jump_target = instr.offset in targets


class Instruction(object):
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
    def code(self):
        '''Return the code string for this instruction.

        .. note:: If the opcode contains an argument which is bigger than the
           available two bytes, the opcode will be prepended by an
           EXTENDED_ARG.

        '''
        import array
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
        res = array.array('B')
        res.fromstring(''.join(chr(b) for b in bytes_))
        tobytes = getattr(res, 'tobytes', res.tostring)
        return tobytes()

    @property
    def size(self):
        import dis
        return 1 if self.opcode < dis.HAVE_ARGUMENT else 3

    @property
    def _instruction(self):
        return BaseInstruction(*tuple(self))

    def _asdict(self):
        from xoutil.collections import OrderedDict
        return OrderedDict([
            (field, getattr(self, field))
            for field in BaseInstruction._fields
        ])

    def __iter__(self):
        return iter(self._asdict().values())

    def __repr__(self):
        return repr(self._instruction)

    def __eq__(self, other):
        from xoutil.objects import validate_attrs
        return validate_attrs(self, other,
                              force_equals=BaseInstruction._fields)


class Token(object):
    """Class representing a byte-code token.

    A byte-code token is equivalent to the contents of one line
    as output by dis.dis().

    """
    def __init__(self, name, arg=None, argval=None,
                 offset=-1, starts_line=False, instruction=None):
        self.name = intern(str(name))
        self.arg = arg
        self.argval = argval
        self.offset = offset
        self.starts_line = starts_line
        self.instruction = instruction

    @classmethod
    def from_instruction(cls, instruction):
        return cls(
            instruction.opname,
            arg=instruction.arg,
            argval=instruction.argval,
            offset=instruction.offset,
            starts_line=instruction.starts_line,
            instruction=instruction
        )

    @property
    def type(self):
        # Several parts of the parser and walker assume a type attribute.  This is consistent with the type attribute for rules.
        return self.name

    def __cmp__(self, o):
        if isinstance(o, Token):
            # both are tokens: compare type and pattr
            return cmp(self.name, o.name) or cmp(self.argval, o.argval)
        else:
            return cmp(self.name, o)

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


class Code(object):
    """Class for representing code-objects.

    This is similar to the original code object, but additionally
    the diassembled code is stored in the attribute '_tokens'.

    """
    def __init__(self, co, scanner, classname=None):
        for i in dir(co):
            if i.startswith('co_'):
                setattr(self, i, getattr(co, i))
        self._tokens, self._customize = scanner.disassemble(co, classname)


class Structure(object):
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


class Scanner(object):
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

    def disassemble(self, co, classname=None):
        'Produce the tokens for the code.'
        result = []
        customizations = {}
        # The 'jumps' is filled by the `detect_structure` closure function
        # below.  It maps the offset of jumping instructions to the farthest
        # offset within the instruction 'structure'.  This allows to keep
        # track of nested boolean and conditional expressions.  The structures
        # are simply the span of instructions pertaining a single (outer)
        # expression.  Some optimization steps make jumps outside the outer
        # structures, jumps keep the right 'target' for those.
        jumps = {}
        BOOLSTRUCT = 'and/or'  # mark for nested conditionals
        structures = []

        def get_target_offset(inst):
            if inst.opcode in dis.hasjabs:
                target = inst.argval
            elif inst.opcode in dis.hasjrel:
                target = inst.argval + inst.offset + inst.size
            else:
                raise ScannerError(
                    'Instruction %s has no target' % inst.opname
                )
            return target

        def get_instruction_at(offset, instructions):
            return next(i for i in enumerate(instructions) if i[-1].offset == offset)

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
                target = get_target_offset(instruction)
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
                if target > offset and above_target.opcode in CONDITIONAL_JUMPs or above_target.opcode == RETURN_VALUE:
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
                target = get_target_offset(instruction)
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
                            label = argval  + offset + size
                        elif opcode in JUMP_IF_OR_POPs and argval > offset:
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
            emit(Token('COME_FROM', COME_FROM, repr(target),
                       offset="%s_%d" % (offset, index)))

        def customize(instruction):
            opname, arg = instruction.opname, instruction.arg
            opname = '%s_%d' % (opname, arg)
            customizations[opname] = arg
            instruction.opname = opname

        instructions = list(without_nops(normalize_pypy_conditional(
            Instruction(i) for i in Bytecode(co)
        )))
        targets = find_jump_targets(instructions)
        for index, instruction in enumerate(instructions):
            opcode = instruction.opcode
            offset = instruction.offset
            _jumps = targets.get(offset, [])
            for k, j in enumerate(_jumps):
                emit_come_from(offset, j, k)
            if opcode in CUSTOMIZABLE:
                customize(instruction)
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

    def __disassemble(self, co, classname=None):
        """Disassemble a code object, returning a list of 'Token'.

        The main part of this procedure is modelled after
        dis.disassemble().

        """
        self.instructions = instructions = list(Bytecode(co))
        rv = []
        customize = {}
        # Token = self.Token  # shortcut
        code = self.code = array(str('B'), co.co_code)
        linestarts = [
            (inst.offset, inst.starts_line)
            for inst in instructions
            if inst.starts_line is not None
        ]
        linestartoffsets = {a for (a, _) in linestarts}
        varnames = tuple(co.co_varnames)
        n = self.get_code_size()
        # An index from byte-code index to the index containing the opcode
        self.prev = prev = [0]
        for inst in instructions:
            # All byte-code operations are 2 bytes or 4 bytes longs, op_size
            # yields the "extra" byte an opcode has: 1 or 3.
            prev.extend((inst.offset, ) * self.op_size(inst.opcode))
        self.lines = []
        linetuple = namedtuple('linetuple', ['l_no', 'next'])
        j = 0
        _, prev_line_no = linestarts[0]
        for (start_byte, line_no) in linestarts[1:]:
            while j < start_byte:
                self.lines.append(linetuple(prev_line_no, start_byte))
                j += 1
            prev_line_no = line_no
        while j < n:
            self.lines.append(linetuple(prev_line_no, n))
            j += 1
        free = co.co_cellvars + co.co_freevars
        names = co.co_names
        # cf: A cross-reference index: keys are offsets that are targets of
        # jumps located in the values.
        cf = self.find_jump_targets(code)
        extended_arg = 0
        for offset in self.op_range(0, n):
            if offset in cf:
                for k, j in enumerate(cf[offset]):
                    rv.append(
                        Token('COME_FROM', None, repr(j),
                              offset="%s_%d" % (offset, k))
                    )
            op = code[offset]
            opname = dis.opname[op]
            arg = argval = None
            if op >= HAVE_ARGUMENT:
                arg = code[offset+1] + code[offset+2] * 256 + extended_arg
                extended_arg = 0
                if op == dis.EXTENDED_ARG:
                    extended_arg = arg * 65536
                    continue
                if op in dis.hasconst:
                    const = co.co_consts[arg]
                    if isinstance(const, types.CodeType):
                        argval = const
                        if const.co_name == '<lambda>':
                            assert opname == 'LOAD_CONST'
                            opname = 'LOAD_LAMBDA'
                        elif const.co_name == '<genexpr>':
                            opname = 'LOAD_GENEXPR'
                        elif const.co_name == '<dictcomp>':
                            opname = 'LOAD_DICTCOMP'
                        elif const.co_name == '<setcomp>':
                            opname = 'LOAD_SETCOMP'
                elif op in dis.hasname:
                    argval = names[arg]
                elif op in dis.hasjrel:
                    argval = repr(offset + 3 + arg)
                elif op in dis.hasjabs:
                    argval = repr(arg)
                elif op in dis.haslocal:
                    argval = varnames[arg]
                elif op in dis.hascompare:
                    argval = dis.cmp_op[arg]
                elif op in dis.hasfree:
                    argval = free[arg]

            if op in CUSTOMIZABLE:
                # CE - Hack for >= 2.5
                #      Now all values loaded via LOAD_CLOSURE are packed into
                #      a tuple before calling MAKE_CLOSURE.
                #
                # BUILD_TUPLE   n
                # if the opcode in `n` is a LOAD_CLOSURE
                if op == BUILD_TUPLE and code[self.prev[offset]] == LOAD_CLOSURE:
                    continue
                else:
                    opname = '%s_%d' % (opname, arg)
                    if op != BUILD_SLICE:
                        customize[opname] = arg
            elif op == JUMP_ABSOLUTE:
                target = self.get_target(offset)
                if target < offset:
                    if offset in self.stmts and code[offset+3] not in (END_FINALLY, POP_BLOCK) \
                       and offset not in self.not_continue:
                        opname = 'CONTINUE'
                    else:
                        opname = 'JUMP_BACK'
            elif op == RETURN_VALUE:
                if offset in self.return_end_ifs:
                    opname = 'RETURN_END_IF'
            rv.append(Token(opname, arg=arg, argval=argval, offset=offset,
                            starts_line=offset in linestartoffsets))
        return rv, customize

    def get_target(self, pos, op=None):
        '''Get the "target" for a JUMP byte-code in offset `pos`.

        '''
        if op is None:
            op = self.code[pos]
        target = self.code[pos+1] + self.code[pos+2] * 256
        if op in dis.hasjrel:
            target += pos + 3
        else:
            assert op in dis.hasjabs
        return target

    def first_instr(self, start, end, instr, target=None, exact=True):
        """Find the first <instr> in the block from start to end.

        <instr> is any python bytecode instruction or a list of opcodes.  If
        <instr> is an opcode with a target (like a jump), a target destination
        can be specified which must match precisely if exact is True, or if
        exact is False, the instruction which has a target closest to <target>
        will be returned.

        Return index to it or None if not found.

        """
        from xoutil.types import is_collection
        instructions = self.instructions
        _len = self.get_code_size()
        assert start >= 0 and end <= _len
        if not is_collection(instr):
            instr = [instr]
        pos = None
        distance = _len
        for instruction in instructions:
            if instruction.opcode in instr:
                if target is None:
                    return instruction.offset
                dest = self.get_target(instruction.offset)
                if dest == target:
                    return instruction.offset
                elif not exact:
                    _distance = abs(target - dest)
                    if _distance < distance:
                        distance = _distance
                        pos = instruction.offset
        return pos

    def last_instr(self, start, end, instr, target=None, exact=True):
        """Find the last <instr> in the block from start to end.

        <instr> is any python bytecode instruction or a list of opcodes.  If
        <instr> is an opcode with a target (like a jump), a target destination
        can be specified which must match precisely if exact is True, or if
        exact is False, the instruction which has a target closest to <target>
        will be returned.

        Return index to it or None if not found.

        """
        from xoutil.types import is_collection
        instructions = self.instructions
        _len = self.get_code_size()
        if not (start >= 0 and end <= _len):
            return None
        if not is_collection(instr):
            instr = [instr]
        pos = None
        distance = _len
        for instruction in instructions:
            if instruction.opcode in instr:
                if target is None:
                    pos = instruction.offset
                else:
                    dest = self.get_target(instruction.offset)
                    if dest == target:
                        distance = 0
                        pos = instruction.offset
                    elif not exact:
                        _distance = abs(target - dest)
                        if _distance <= distance:
                            distance = _distance
                            pos = instruction.offset
        return pos

    def all_instr(self, start, end, instr, target=None,
                  include_beyond_target=False):
        """Find all <instr> in the block from start to end.

        <instr> is any python bytecode instruction or a list of opcodes.  If
        <instr> is an opcode with a target (like a jump), a target destination
        can be specified which must match precisely.

        Return a list with indexes to them or [] if none found.

        """
        code = self.code
        assert(start >= 0 and end <= len(code))
        try:
            None in instr
        except:
            instr = [instr]
        result = []
        for i in self.op_range(start, end):
            op = code[i]
            if op in instr:
                if target is None:
                    result.append(i)
                else:
                    t = self.get_target(i, op)
                    if include_beyond_target and t >= target:
                        result.append(i)
                    elif t == target:
                        result.append(i)
        return result

    def op_size(self, op):
        if op < HAVE_ARGUMENT:
            return 1
        else:
            return 3

    def op_range(self, start, end):
        while start < end:
            yield start
            start += self.op_size(self.code[start])

    def get_code_size(self):
        i = self.instructions[-1]
        return i.offset + self.op_size(i.opcode)

    def build_stmt_indices(self):
        code = self.code
        start = 0
        end = len(code)
        stmt_opcodes = {
            SETUP_LOOP, BREAK_LOOP, CONTINUE_LOOP,
            SETUP_FINALLY, END_FINALLY, SETUP_EXCEPT, SETUP_WITH,
            POP_BLOCK, STORE_FAST, DELETE_FAST, STORE_DEREF,
            STORE_GLOBAL, DELETE_GLOBAL, STORE_NAME, DELETE_NAME,
            STORE_ATTR, DELETE_ATTR, STORE_SUBSCR, DELETE_SUBSCR,
            RETURN_VALUE, RAISE_VARARGS, POP_TOP,
            PRINT_EXPR, PRINT_ITEM, PRINT_NEWLINE, PRINT_ITEM_TO,
            PRINT_NEWLINE_TO,
            STORE_SLICE_0, STORE_SLICE_1, STORE_SLICE_2, STORE_SLICE_3,
            DELETE_SLICE_0, DELETE_SLICE_1, DELETE_SLICE_2, DELETE_SLICE_3,
            JUMP_ABSOLUTE, EXEC_STMT,
        }
        stmt_opcode_seqs = [
            (POP_JUMP_IF_FALSE, JUMP_FORWARD),
            (POP_JUMP_IF_FALSE, JUMP_ABSOLUTE),
            (POP_JUMP_IF_TRUE, JUMP_FORWARD),
            (POP_JUMP_IF_TRUE, JUMP_ABSOLUTE)
        ]
        designator_ops = {
            STORE_FAST, STORE_NAME, STORE_GLOBAL, STORE_DEREF, STORE_ATTR,
            STORE_SLICE_0, STORE_SLICE_1, STORE_SLICE_2, STORE_SLICE_3,
            STORE_SUBSCR, UNPACK_SEQUENCE, JUMP_ABSOLUTE
        }
        prelim = self.all_instr(start, end, stmt_opcodes)
        stmts = self.stmts = set(prelim)
        pass_stmts = set()
        for seq in stmt_opcode_seqs:
            for i in self.op_range(start, end-(len(seq)+1)):
                match = True
                for elem in seq:
                    if elem != code[i]:
                        match = False
                        break
                    i += self.op_size(code[i])
                if match:
                    i = self.prev[i]
                    stmts.add(i)
                    pass_stmts.add(i)
        if pass_stmts:
            stmt_list = list(stmts)
            stmt_list.sort()
        else:
            stmt_list = prelim
        last_stmt = -1
        slist = self.next_stmt = []
        i = 0
        for s in stmt_list:
            if code[s] == JUMP_ABSOLUTE and s not in pass_stmts:
                target = self.get_target(s)
                if target > s or self.lines[last_stmt].l_no == self.lines[s].l_no:
                    stmts.remove(s)
                    continue
                j = self.prev[s]
                while code[j] == JUMP_ABSOLUTE:
                    j = self.prev[j]
                if code[j] == LIST_APPEND:  # list comprehension
                    stmts.remove(s)
                    continue
            elif code[s] == POP_TOP and code[self.prev[s]] == ROT_TWO:
                stmts.remove(s)
                continue
            elif code[s] in designator_ops:
                j = self.prev[s]
                while code[j] in designator_ops:
                    j = self.prev[j]
                if code[j] == FOR_ITER:
                    stmts.remove(s)
                    continue
            last_stmt = s
            slist += [s] * (s-i)
            i = s
        slist += [len(code)] * (len(code)-len(slist))

    def remove_mid_line_ifs(self, ifs):
        filtered = []
        for i in ifs:
            if self.lines[i].l_no == self.lines[i+3].l_no:
                if self.code[self.prev[self.lines[i].next]] in POP_JUMP_IFs:
                    continue
            filtered.append(i)
        return filtered

    def rem_or(self, start, end, instr, target=None,
               include_beyond_target=False):
        """Find all <instr> in the block from start to end.

        <instr> is any python bytecode instruction or a list of opcodes.  If
        <instr> is an opcode with a target (like a jump), a target destination
        can be specified which must match precisely.

        Return a list with indexes to them or [] if none found.

        """
        code = self.code
        assert(start >= 0 and end <= len(code))
        try:
            None in instr
        except:
            instr = [instr]
        result = []
        for i in self.op_range(start, end):
            op = code[i]
            if op in instr:
                if target is None:
                    result.append(i)
                else:
                    t = self.get_target(i, op)
                    if include_beyond_target and t >= target:
                        result.append(i)
                    elif t == target:
                        result.append(i)
        pjits = self.all_instr(start, end, POP_JUMP_IF_TRUE)
        filtered = []
        for pjit in pjits:
            tgt = self.get_target(pjit)-3
            for i in result:
                if i <= pjit or i >= tgt:
                    filtered.append(i)
            result = filtered
            filtered = []
        return result

    def next_except_jump(self, start):
        """Return the next jump that was generated by an except SomeException:
        construct in a try...except...else clause or None if not found.

        """
        if self.code[start] == DUP_TOP:
            except_match = self.first_instr(start, len(self.code),
                                            POP_JUMP_IF_FALSE)
            if except_match:
                jmp = self.prev[self.get_target(except_match)]
                self.ignore_if.add(except_match)
                self.not_continue.add(jmp)
                return jmp
        count_END_FINALLY = 0
        count_SETUP_ = 0
        for i in self.op_range(start, len(self.code)):
            op = self.code[i]
            if op == END_FINALLY:
                if count_END_FINALLY == count_SETUP_:
                    assert self.code[self.prev[i]] in UNCONDITIONAL_JUMPs + (RETURN_VALUE, )
                    self.not_continue.add(self.prev[i])
                    return self.prev[i]
                count_END_FINALLY += 1
            elif op in (SETUP_EXCEPT, SETUP_WITH, SETUP_FINALLY):
                count_SETUP_ += 1

    def restrict_to_parent(self, target, parent):
        """Return the target within the parent structure boundaries.

        If `target` is not completely contained within the parent boundaries,
        return the end of the of the parent.  Otherwise, return `target`.

        """
        if not (parent['start'] < target < parent['end']):
            target = parent['end']
        return target

    def get_parent_structure(self, offset):
        '''The minimal structure the given `offset` lies into.

        Since structures don't overlap unless fully contained they form a
        nested structure.  Minimal means there's no an inner structure which
        contains the given `offset`.

        An offset at the very end of a structure is part of the parent
        structure.  An offset at the start of a structure is part of it.

        In the diagram shown below dots are offsets, delimiter show the start
        and end of structures.

        ::

            1     2        3       4                5
            [     (    )   (       {       }   )    (  )]
            .............................................
                  ^            ^       ^   ^
                  At 2         |       |   Not at 4
                               At 3    |
                                       At 4

        '''
        parent = self.structs[0]
        the_start, the_end = parent['start'], parent['end']
        for struct in self.structs[1:]:
            start = struct['start']
            end = struct['end']
            if the_start <= start <= offset < end <= the_end:
                the_start = start
                the_end = end
                parent = struct
        return parent

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
                structs.append({'type':  'and/or',
                                'start': start,
                                'end':   pre[target]})
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
                            and self.restrict_to_parent(self.get_target(pre[rtarget]), parent) == rtarget:
                        if code[pre[pre[rtarget]]] == JUMP_ABSOLUTE \
                                and self.remove_mid_line_ifs([pos]) \
                                and target == self.get_target(pre[pre[rtarget]]) \
                                and (pre[pre[rtarget]] not in self.stmts or self.get_target(pre[pre[rtarget]]) > pre[pre[rtarget]])\
                                and 1 == len(self.remove_mid_line_ifs(self.rem_or(start, pre[pre[rtarget]], POP_JUMP_IFs, target))):
                            pass
                        elif code[pre[pre[rtarget]]] == RETURN_VALUE \
                                and self.remove_mid_line_ifs([pos]) \
                                and 1 == (len(set(self.remove_mid_line_ifs(self.rem_or(start, pre[pre[rtarget]], \
                                                             POP_JUMP_IFs, target))) \
                                              | set(self.remove_mid_line_ifs(self.rem_or(start, pre[pre[rtarget]], \
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
                structs.append({'type':  'if-then',
                                'start': start,
                                'end':   pre[rtarget]})
                self.not_continue.add(pre[rtarget])
                if rtarget < end:
                    structs.append({'type':  'if-else',
                                    'start': rtarget,
                                    'end':   end})
            elif code[pre[rtarget]] == RETURN_VALUE:
                structs.append({'type':  'if-then',
                                'start': start,
                                'end':   rtarget})
                self.return_end_ifs.add(pre[rtarget])
        elif op in JUMP_IF_OR_POPs:
            target = self.get_target(pos, op)
            self.fixed_jumps[pos] = self.restrict_to_parent(target, parent)

    def find_jump_targets(self, code):
        """Detect all offsets in a byte code which are jump targets.

        Return the list of offsets.

        This procedure is modelled after dis.findlables(), but here for each
        target the number of jumps are counted.

        """
        hasjrel = dis.hasjrel
        hasjabs = dis.hasjabs
        # Structs holds the current structures found in the bytecode the
        # 'root' struct is the entire program and it spans from the first
        # byte-code (offset 0) to the last (offset n-1).  The
        # `detect_structure` method fills this data-structure with minor
        # structures like loops, etc.
        self.structs = structs = [{'type':  'root',
                                   'start': 0,
                                   'end':   self.get_code_size()-1}]
        self.loops = []  # All loop entry points
        self.fixed_jumps = {}  # Map fixed jumps to their real destination
        self.ignore_if = set()
        self.build_stmt_indices()
        self.not_continue = set()
        self.return_end_ifs = set()
        targets = {}
        for instr in self.instructions:
            # Determine structures and fix jumps for 2.3+
            # this method fills `self.fixed_jumps`.
            self.detect_structure(instr.offset, instr.opcode, structs=structs)
            op = instr.opcode
            offset = instr.offset
            if op >= HAVE_ARGUMENT:
                label = self.fixed_jumps.get(offset)
                oparg = instr.arg
                if label is None:
                    if op in hasjrel and op != FOR_ITER:
                        label = offset + 3 + oparg
                    elif op in hasjabs:
                        if op in JUMP_IF_OR_POPs and oparg > offset:
                            label = oparg
                if label is not None and label != -1:
                    targets.setdefault(label, []).append(offset)
        return targets


# A cache from version to Scanners.
# Since Scanners are not thread-safe the getscanner accepts a
# get_current_thread argument so that scanners don't cross threads.
__scanners = {}


try:
    from thread import get_ident
except ImportError:
    from _thread import get_ident


def getscanner(version=None, get_current_thread=get_ident):
    from xoutil import Unset
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


# Local Variables:
# fill-column: 150
# End:

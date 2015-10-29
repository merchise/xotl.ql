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

#  We'll only support 2.7 and 3.2+
from sys import version_info as _vinfo
assert _vinfo >= (2, 7, 0) and (not _vinfo >= (3, 0) or _vinfo >= (3, 2))
del _vinfo

try:
    from sys import intern  # Py3k
except ImportError:
    from __builtin__ import intern

HAVE_ARGUMENT = dis.HAVE_ARGUMENT

globals().update(
    {k.replace('+', '_'): v for (k, v) in list(dis.opmap.items())}
)

from xoutil.eight import _py3, _py2
if _py3:
    PRINT_ITEM = PRINT_ITEM_TO = PRINT_NEWLINE = PRINT_NEWLINE_TO = None
    STORE_SLICE_0 = STORE_SLICE_1 = STORE_SLICE_2 = STORE_SLICE_3 = None
    DELETE_SLICE_0 = DELETE_SLICE_1 = DELETE_SLICE_2 = DELETE_SLICE_3 = None
    EXEC_STMT = None
    DUP_TOPX = None

if _py2:
    DUP_TOP_TWO = None
    LOAD_BUILD_CLASS = None

del _py3, _py2

JUMP_IF_OR_POPs = (JUMP_IF_TRUE_OR_POP, JUMP_IF_FALSE_OR_POP)
POP_JUMP_IFs = (POP_JUMP_IF_TRUE, POP_JUMP_IF_FALSE)
POP_JUMPs = JUMP_IF_OR_POPs + POP_JUMP_IFs

JUMPs = (JUMP_ABSOLUTE, JUMP_FORWARD)


class Token(object):
    """Class representing a byte-code token.

    A byte-code token is equivalent to the contents of one line
    as output by dis.dis().

    """
    def __init__(self, type_, attr=None, pattr=None, offset=-1,
                 linestart=False):
        self.type = intern(str(type_))
        self.attr = attr
        self.pattr = pattr
        self.offset = offset
        self.linestart = linestart

    def __cmp__(self, o):
        if isinstance(o, Token):
            # both are tokens: compare type and pattr
            return cmp(self.type, o.type) or cmp(self.pattr, o.pattr)
        else:
            return cmp(self.type, o)

    def __repr__(self):
        return '<%s(%s, %s): %s>' % (str(self.type), self.attr, self.pattr, self.offset)

    def __str__(self):
        pattr = self.pattr
        if self.linestart:
            return '\n%s\t%-17s %r' % (self.offset, self.type, pattr)
        else:
            return '%s\t%-17s %r' % (self.offset, self.type, pattr)

    def __hash__(self):
        return hash(self.type)

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
        """Disassemble a code object, returning a list of 'Token'.

        The main part of this procedure is modelled after
        dis.disassemble().

        """
        rv = []
        customize = {}
        Token = self.Token  # shortcut
        code = self.code = array(str('B'), co.co_code)
        linestarts = list(dis.findlinestarts(co))
        varnames = tuple(co.co_varnames)
        n = len(code)

        # An index from byte-code index to the index containing the opcode
        self.prev = prev = [0]
        for i in self.op_range(0, n):
            op = code[i]
            prev.append(i)
            if op >= HAVE_ARGUMENT:
                prev.append(i)
                prev.append(i)

        self.lines = []
        linetuple = namedtuple('linetuple', ['l_no', 'next'])
        j = 0

        linestartoffsets = {a for (a, _) in linestarts}
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
        # cf:  A cross-reference index:  keys are offsets that are targets of jumps located in the values.
        cf = self.find_jump_targets(code)
        extended_arg = 0
        for offset in self.op_range(0, n):
            if offset in cf:
                for k, j in enumerate(cf[offset]):
                    rv.append(Token('COME_FROM', None, repr(j),
                                    offset="%s_%d" % (offset, k)))
            op = code[offset]
            opname = dis.opname[op]
            oparg = pattr = None
            if op >= HAVE_ARGUMENT:
                oparg = code[offset+1] + code[offset+2] * 256 + extended_arg
                extended_arg = 0
                if op == dis.EXTENDED_ARG:
                    extended_arg = oparg * 65536
                    continue
                if op in dis.hasconst:
                    const = co.co_consts[oparg]
                    if isinstance(const, types.CodeType):
                        oparg = const
                        if const.co_name == '<lambda>':
                            assert opname == 'LOAD_CONST'
                            opname = 'LOAD_LAMBDA'
                        elif const.co_name == '<genexpr>':
                            opname = 'LOAD_GENEXPR'
                        elif const.co_name == '<dictcomp>':
                            opname = 'LOAD_DICTCOMP'
                        elif const.co_name == '<setcomp>':
                            opname = 'LOAD_SETCOMP'
                        # verify uses 'pattr' for comparism, since 'attr'
                        # now holds Code(const) and thus can not be used
                        # for comparism (todo: think about changing this)
                        pattr = '<code_object ' + const.co_name + '>'
                    else:
                        pattr = const
                elif op in dis.hasname:
                    pattr = names[oparg]
                elif op in dis.hasjrel:
                    pattr = repr(offset + 3 + oparg)
                elif op in dis.hasjabs:
                    pattr = repr(oparg)
                elif op in dis.haslocal:
                    pattr = varnames[oparg]
                elif op in dis.hascompare:
                    pattr = dis.cmp_op[oparg]
                elif op in dis.hasfree:
                    pattr = free[oparg]

            if op in (BUILD_LIST, BUILD_TUPLE, BUILD_SET, BUILD_SLICE,
                      UNPACK_SEQUENCE,
                      MAKE_FUNCTION, CALL_FUNCTION, MAKE_CLOSURE,
                      CALL_FUNCTION_VAR, CALL_FUNCTION_KW,
                      CALL_FUNCTION_VAR_KW, DUP_TOPX, RAISE_VARARGS):
                # CE - Hack for >= 2.5
                #      Now all values loaded via LOAD_CLOSURE are packed into
                #      a tuple before calling MAKE_CLOSURE.
                if op == BUILD_TUPLE \
                   and code[self.prev[offset]] == LOAD_CLOSURE:
                    continue
                else:
                    opname = '%s_%d' % (opname, oparg)
                    if op != BUILD_SLICE:
                        customize[opname] = oparg
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
            rv.append(Token(opname, oparg, pattr, offset,
                            linestart=offset in linestartoffsets))
        return rv, customize

    def get_target(self, pos, op=None):
        if op is None:
            op = self.code[pos]
        target = self.code[pos+1] + self.code[pos+2] * 256
        if op in dis.hasjrel:
            target += pos + 3
        return target

    def first_instr(self, start, end, instr, target=None, exact=True):
        """Find the first <instr> in the block from start to end.

        <instr> is any python bytecode instruction or a list of opcodes If
        <instr> is an opcode with a target (like a jump), a target destination
        can be specified which must match precisely if exact is True, or if
        exact is False, the instruction which has a target closest to <target>
        will be returned.

        Return index to it or None if not found.

        """
        from xoutil.types import is_collection
        code = self.code
        assert start >= 0 and end <= len(code)
        if not is_collection(instr):
            instr = [instr]
        pos = None
        distance = len(code)
        for i in self.op_range(start, end):
            op = code[i]
            if op in instr:
                if target is None:
                    return i
                dest = self.get_target(i, op)
                if dest == target:
                    return i
                elif not exact:
                    _distance = abs(target - dest)
                    if _distance < distance:
                        distance = _distance
                        pos = i
        return pos

    def last_instr(self, start, end, instr, target=None, exact=True):
        """Find the last <instr> in the block from start to end.

        <instr> is any python bytecode instruction or a list of opcodes If
        <instr> is an opcode with a target (like a jump), a target destination
        can be specified which must match precisely if exact is True, or if
        exact is False, the instruction which has a target closest to <target>
        will be returned.

        Return index to it or None if not found.

        """
        from xoutil.types import is_collection
        code = self.code
        if not (start >= 0 and end <= len(code)):
            return None
        if not is_collection(instr):
            instr = [instr]
        pos = None
        distance = len(code)
        for i in self.op_range(start, end):
            op = code[i]
            if op in instr:
                if target is None:
                    pos = i
                else:
                    dest = self.get_target(i, op)
                    if dest == target:
                        distance = 0
                        pos = i
                    elif not exact:
                        _distance = abs(target - dest)
                        if _distance <= distance:
                            distance = _distance
                            pos = i
        return pos

    def all_instr(self, start, end, instr, target=None,
                  include_beyond_target=False):
        """Find all <instr> in the block from start to end.

        <instr> is any python bytecode instruction or a list of opcodes If
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
        self.next_stmt = []
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

        <instr> is any python bytecode instruction or a list of opcodes If
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
                    assert self.code[self.prev[i]] in JUMPs + (RETURN_VALUE, )
                    self.not_continue.add(self.prev[i])
                    return self.prev[i]
                count_END_FINALLY += 1
            elif op in (SETUP_EXCEPT, SETUP_WITH, SETUP_FINALLY):
                count_SETUP_ += 1

    def restrict_to_parent(self, target, parent):
        """Restrict pos to parent boundaries."""
        if not (parent['start'] < target < parent['end']):
            target = parent['end']
        return target

    def detect_structure(self, pos, op=None):
        """Detect structures and their boundaries to fix optimized jumps in
        python2.3+

        """
        # TODO: check the struct boundaries more precisely -Dan
        code = self.code
        # Ev remove this test and make op a mandatory argument -Dan
        if op is None:
            op = code[pos]
        # Detect parent structure
        parent = self.structs[0]
        start = parent['start']
        end = parent['end']
        for s in self.structs:
            _start = s['start']
            _end = s['end']
            if (_start <= pos < _end) and (_start >= start and _end <= end):
                start = _start
                end = _end
                parent = s
        # We need to know how many new structures were added in this run
        if op == SETUP_LOOP:
            start = pos+3
            target = self.get_target(pos, op)
            end = self.restrict_to_parent(target, parent)
            if target != end:
                self.fixed_jumps[pos] = end

            (line_no, next_line_byte) = self.lines[pos]
            jump_back = self.last_instr(start, end, JUMP_ABSOLUTE,
                                        next_line_byte, False)

            if jump_back and jump_back != self.prev[end] and code[jump_back+3] in JUMPs:
                if code[self.prev[end]] == RETURN_VALUE or \
                      (code[self.prev[end]] == POP_BLOCK and code[self.prev[self.prev[end]]] == RETURN_VALUE):
                    jump_back = None

            if not jump_back:  # loop suite ends in return. wtf right?
                jump_back = self.last_instr(start, end, RETURN_VALUE) + 1
                if not jump_back:
                    return
                if code[self.prev[next_line_byte]] not in POP_JUMP_IFs:
                    loop_type = 'for'
                else:
                    loop_type = 'while'
                    self.ignore_if.add(self.prev[next_line_byte])
                target = next_line_byte
                end = jump_back + 3
            else:
                if self.get_target(jump_back) >= next_line_byte:
                    jump_back = self.last_instr(start, end, JUMP_ABSOLUTE,
                                                start, False)

                if end > jump_back+4 and code[end] in JUMPs:
                    if code[jump_back+4] in JUMPs:
                        if self.get_target(jump_back+4) == self.get_target(end):
                            self.fixed_jumps[pos] = jump_back+4
                            end = jump_back+4
                elif target < pos:
                    self.fixed_jumps[pos] = jump_back+4
                    end = jump_back+4

                target = self.get_target(jump_back, JUMP_ABSOLUTE)

                if code[target] in (FOR_ITER, GET_ITER):
                    loop_type = 'for'
                else:
                    loop_type = 'while'
                    test = self.prev[next_line_byte]
                    if test == pos:
                        loop_type = 'while 1'
                    else:
                        self.ignore_if.add(test)
                        test_target = self.get_target(test)
                        if test_target > (jump_back+3):
                            jump_back = test_target

                self.not_continue.add(jump_back)

            self.loops.append(target)
            self.structs.append({'type': loop_type + '-loop',
                                 'start': target,
                                 'end':   jump_back})
            if jump_back+3 != end:
                self.structs.append({'type': loop_type + '-else',
                                     'start': jump_back+3,
                                     'end':   end})
        elif op == SETUP_EXCEPT:
            start = pos+3
            target = self.get_target(pos, op)
            end = self.restrict_to_parent(target, parent)
            if target != end:
                self.fixed_jumps[pos] = end
            # Add the try block
            self.structs.append({'type':  'try',
                                 'start': start,
                                 'end':   end-4})
            # Now isolate the except and else blocks
            end_else = start_else = self.get_target(self.prev[end])

            # Add the except blocks
            i = end
            while self.code[i] != END_FINALLY:
                jmp = self.next_except_jump(i)
                if self.code[jmp] == RETURN_VALUE:
                    self.structs.append({'type':  'except',
                                         'start': i,
                                         'end':   jmp+1})
                    i = jmp + 1
                else:
                    if self.get_target(jmp) != start_else:
                        end_else = self.get_target(jmp)
                    if self.code[jmp] == JUMP_FORWARD:
                        self.fixed_jumps[jmp] = -1
                    self.structs.append({'type':  'except',
                                         'start': i,
                                         'end':   jmp})
                    i = jmp + 3

            # Add the try-else block
            if end_else != start_else:
                r_end_else = self.restrict_to_parent(end_else, parent)
                self.structs.append({'type':  'try-else',
                                     'start': i+1,
                                     'end':   r_end_else})
                self.fixed_jumps[i] = r_end_else
            else:
                self.fixed_jumps[i] = i+1
        elif op in POP_JUMP_IFs:
            start = pos+3
            target = self.get_target(pos, op)
            rtarget = self.restrict_to_parent(target, parent)
            pre = self.prev

            if target != rtarget and parent['type'] == 'and/or':
                self.fixed_jumps[pos] = rtarget
                return
            # does this jump to right after another cond jump?
            # if so, it's part of a larger conditional
            if (code[pre[target]] in POP_JUMPs) and (target > pos):
                self.fixed_jumps[pos] = pre[target]
                self.structs.append({'type':  'and/or',
                                     'start': start,
                                     'end':   pre[target]})
                return

            # is this an if and
            if op == POP_JUMP_IF_FALSE:
                match = self.rem_or(start, self.next_stmt[pos], POP_JUMP_IF_FALSE, target)
                match = self.remove_mid_line_ifs(match)
                if match:
                    if code[pre[rtarget]] in JUMPs \
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
                if (pos+3) in self.load_asserts:
                    if code[pre[rtarget]] == RAISE_VARARGS:
                        return
                    self.load_asserts.remove(pos+3)

                next = self.next_stmt[pos]
                if pre[next] == pos:
                    pass
                elif code[next] in JUMPs and target == self.get_target(next):
                    if code[pre[next]] == POP_JUMP_IF_FALSE:
                        if code[next] == JUMP_FORWARD or target != rtarget or code[pre[pre[rtarget]]] not in JUMPs:
                            self.fixed_jumps[pos] = pre[next]
                            return
                elif code[next] == JUMP_ABSOLUTE and code[target] in JUMPs:
                    next_target = self.get_target(next)
                    if self.get_target(target) == next_target:
                        self.fixed_jumps[pos] = pre[next]
                        return
                    elif code[next_target] in JUMPs and self.get_target(next_target) == self.get_target(target):
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
            if code[pre[rtarget]] in JUMPs:
                if_end = self.get_target(pre[rtarget])

                # is this a loop not an if?
                if if_end < pre[rtarget] and code[pre[if_end]] == SETUP_LOOP:
                    if if_end > start:
                        return

                end = self.restrict_to_parent(if_end, parent)

                self.structs.append({'type':  'if-then',
                                     'start': start,
                                     'end':   pre[rtarget]})
                self.not_continue.add(pre[rtarget])

                if rtarget < end:
                    self.structs.append({'type':  'if-else',
                                         'start': rtarget,
                                         'end':   end})
            elif code[pre[rtarget]] == RETURN_VALUE:
                self.structs.append({'type':  'if-then',
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
        n = len(code)
        self.structs = [{'type':  'root',
                         'start': 0,
                         'end':   n-1}]
        self.loops = []  # All loop entry points
        self.fixed_jumps = {}  # Map fixed jumps to their real destination
        self.ignore_if = set()
        self.build_stmt_indices()
        self.not_continue = set()
        self.return_end_ifs = set()
        targets = {}
        for i in self.op_range(0, n):
            op = code[i]
            # Determine structures and fix jumps for 2.3+
            self.detect_structure(i, op)
            if op >= HAVE_ARGUMENT:
                label = self.fixed_jumps.get(i)
                oparg = code[i+1] + code[i+2] * 256
                if label is None:
                    if op in hasjrel and op != FOR_ITER:
                        label = i + 3 + oparg
                    elif op in hasjabs:
                        if op in (JUMP_IF_FALSE_OR_POP, JUMP_IF_TRUE_OR_POP):
                            if (oparg > i):
                                label = oparg
                if label is not None and label != -1:
                    targets.setdefault(label, []).append(i)
            elif op == END_FINALLY and i in self.fixed_jumps:
                label = self.fixed_jumps[i]
                targets.setdefault(label, []).append(i)
        return targets


__scanners = {}


def getscanner(version):
    if version not in __scanners:
        __scanners[version] = Scanner(version)
    return __scanners[version]

# Local Variables:
# fill-column: 150
# End:

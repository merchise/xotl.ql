# -*- encoding: utf-8 -*-
# ---------------------------------------------------------------------
# xotl.ql.revenge.parsers
# ---------------------------------------------------------------------
# Copyright (c) 2014-2016 Merchise Autrement and Contributors
# All rights reserved.
#
#  Copyright (c) 2000-2002 by hartmut Goebel <h.goebel@crazy-compilers.com>
#  Copyright (c) 2005 by Dan Pascu <dan@windowmaker.org>
#  Copyright (c) 1999 John Aycock
#
#  See main module for license.
#

# flake8: noqa

from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)

__all__ = ['parse', 'AST', 'ParserError', 'Parser']

from .spark import GenericASTBuilder
from xoutil.collections import UserList

import sys
_py_version = sys.version_info
from .eight import override, py27, py32, py3k, py33, py34, pypy   # noqa
from .exceptions import ParserError as RevengeParserError

try:
    from sys import intern  # Py3k
except ImportError:
    from __builtin__ import intern


class AST(UserList):
    def __init__(self, type, kids=[]):
        self.type = intern(str(type))
        UserList.__init__(self, kids)

    def __getitem__(self, item):
        return self.data[item]

    def __eq__(self, o):
        if isinstance(o, AST):
            return self.type == o.type and UserList.__eq__(self, o)
        else:
            # Don't forbid other types since we may try to compare AST with
            # Tokens.
            return self.type == o

    def __hash__(self):
        return hash(self.type)

    def __repr__(self, indent=''):
        result = ['']

        def pre(who, indent=0):
            result[0] += ' ' * indent
            result[0] += who.type if isinstance(who, AST) else repr(who)
            result[0] += '\n'
            try:
                children = iter(who)
            except TypeError:
                pass
            else:
                for child in children:
                    pre(child, indent=indent+4)

        pre(self)
        return result[0]


class ParserError(RevengeParserError):
    def __init__(self, token, offset, *args):
        super(ParserError, self).__init__(token, offset, *args)
        self.token = token
        self.offset = offset

    def __str__(self):
        return "Syntax error at or near `%r' token at offset %s" % \
            (self.token, self.offset)


class _InternalParser(GenericASTBuilder):
    def __init__(self):
        GenericASTBuilder.__init__(self, AST, 'sstmt')
        self.customized = {}

    def error(self, token):
        raise ParserError(token, token.offset)

    def typestring(self, token):
        return token.name

    def cleanup(self):
        """Remove recursive references.

        Allow the garbage collector to collect this object.

        """
        for dict in (self.rule2func, self.rules, self.rule2name):
            for i in dict:
                dict[i] = None
        for i in dir(self):
            setattr(self, i, None)

    # The rules draw concepts presented in the 'Expressions' document in the
    # Python documentation.  However, the rules there are presented not for
    # lexical analysis, and sometimes are cumbersome to follow.
    #
    # The `yield_atom` is not supported by this grammar since it must occur
    # within a generator definition.
    #

    def p_atoms(self):
        '''The atoms are the most basic element of an expression.

        According to the Python documentation those include: literals,
        identifiers and 'enclosures'.  Since enclosure, however, are actually
        more structured we'll include them later.

        .. _rules:

        expr        ::=  atom
        atom        ::=  identifier | literal
        identifier  ::=  LOAD_FAST | LOAD_NAME | LOAD_GLOBAL | LOAD_DEREF
        literal     ::=  LOAD_CONST

        '''

    def p_mapexpression_common(self, args):
        '''Common rules for map expressions across all Python versions.

        expr ::= mapexpr

        kvlist ::= kvlist kv
        kvlist ::=

        '''

    @override((2, 7) <= _py_version < (3, 5))
    def p_mapexpression(self, args):
        '''A map expression.

        Dictionary literals are built by creating a fixed sized dictionary and
        filling it with they values.

        It starts with a BUILD_MAP followed by the list of (key, value).

        .. _rules:

        mapexpr ::= BUILD_MAP kvlist

        # This is the only one I've witnessed.
        kv3 ::= expr expr STORE_MAP


        # Don't know yet when these are produced for kvlist.
        kvlist ::= kvlist kv2
        kvlist ::= kvlist kv3

        kv ::= DUP_TOP expr ROT_TWO expr STORE_SUBSCR
        kv2 ::= DUP_TOP expr expr ROT_THREE STORE_SUBSCR

        '''

    def p_expr(self, args):
        '''The expression rules.

        expr ::= _mklambda
        expr ::= load_attr
        expr ::= binary_expr
        expr ::= binary_expr_na
        expr ::= build_list
        expr ::= cmp
        expr ::= and
        expr ::= and2
        expr ::= or
        expr ::= unary_expr
        expr ::= call_function
        expr ::= unary_not
        expr ::= unary_convert
        expr ::= binary_subscr
        expr ::= binary_subscr2
        expr ::= get_iter
        expr ::= slice0
        expr ::= slice1
        expr ::= slice2
        expr ::= slice3
        expr ::= buildslice2
        expr ::= buildslice3
        expr ::= yield


        binary_expr ::=  expr expr binary_op

        binary_op ::= BINARY_ADD | BINARY_MULTIPLY | BINARY_AND | BINARY_OR |
                      BINARY_XOR | BINARY_SUBTRACT | BINARY_DIVIDE |
                      BINARY_TRUE_DIVIDE | BINARY_FLOOR_DIVIDE |
                      BINARY_MODULO | BINARY_LSHIFT | BINARY_RSHIFT |
                      BINARY_POWER

        unary_expr ::= expr unary_op
        unary_op ::= UNARY_POSITIVE
        unary_op ::= UNARY_NEGATIVE
        unary_op ::= UNARY_INVERT

        # The ``__unary_not`` simply makes thing easier to implement in the
        # walker of the syntax tree since creates the same depth as in
        # unary_expr.

        unary_not ::= expr __unary_not
        __unary_not ::= UNARY_NOT

        binary_subscr ::= expr expr BINARY_SUBSCR
        binary_subscr2 ::= expr expr DUP_TOPX_2 BINARY_SUBSCR

        load_attr ::= expr LOAD_ATTR
        get_iter ::= expr GET_ITER
        slice0 ::= expr SLICE+0
        slice0 ::= expr DUP_TOP SLICE+0
        slice1 ::= expr expr SLICE+1
        slice1 ::= expr expr DUP_TOPX_2 SLICE+1
        slice2 ::= expr expr SLICE+2
        slice2 ::= expr expr DUP_TOPX_2 SLICE+2
        slice3 ::= expr expr expr SLICE+3
        slice3 ::= expr expr expr DUP_TOPX_3 SLICE+3
        buildslice3 ::= expr expr expr BUILD_SLICE_3
        buildslice2 ::= expr expr BUILD_SLICE_2

        # mklambda
        _mklambda ::= load_closure mklambda
        _mklambda ::= mklambda

        load_closure ::= load_closure LOAD_CLOSURE
        load_closure ::= LOAD_CLOSURE

        .. COME_FROM is a custom token introduced by the scanner so that
        .. we can know the point a jump was made.

        _come_from ::= COME_FROM
        _come_from ::=

        or   ::= expr POP_JUMP_IF_TRUE expr COME_FROM
        or   ::= expr JUMP_IF_TRUE_OR_POP expr COME_FROM
        and  ::= expr POP_JUMP_IF_FALSE expr COME_FROM
        and  ::= expr JUMP_IF_FALSE_OR_POP expr COME_FROM
        and2 ::= _jump POP_JUMP_IF_FALSE COME_FROM expr COME_FROM

        expr ::= conditional

        conditional ::= expr POP_JUMP_IF_FALSE expr JUMP_FORWARD expr
                        COME_FROM
        conditional ::= expr POP_JUMP_IF_FALSE expr JUMP_ABSOLUTE expr

        expr ::= conditionalnot
        conditionalnot ::= expr POP_JUMP_IF_TRUE expr JUMP_FORWARD expr
                           COME_FROM
        conditionalnot ::= expr POP_JUMP_IF_TRUE expr JUMP_ABSOLUTE expr

        ret_expr ::= expr
        ret_expr ::= ret_and
        ret_expr ::= ret_or

        ret_expr_or_cond ::= ret_expr
        ret_expr_or_cond ::= ret_cond
        ret_expr_or_cond ::= ret_cond_not

        ret_and  ::= expr JUMP_IF_FALSE_OR_POP ret_expr_or_cond COME_FROM
        ret_or   ::= expr JUMP_IF_TRUE_OR_POP ret_expr_or_cond COME_FROM
        ret_cond ::= expr POP_JUMP_IF_FALSE expr RETURN_END_IF
                     ret_expr_or_cond
        ret_cond_not ::= expr POP_JUMP_IF_TRUE expr RETURN_END_IF
                         ret_expr_or_cond

        # The LAMBDA_MARKER is actually injected by the walker
        return_lambda ::= ret_expr RETURN_VALUE LAMBDA_MARKER
        conditional_lambda ::= expr POP_JUMP_IF_FALSE return_if_stmt
                               return_stmt LAMBDA_MARKER

        cmp ::= cmp_list
        cmp ::= compare

        compare ::= expr expr COMPARE_OP

        cmp_list ::= expr cmp_list1 ROT_TWO POP_TOP _come_from

        cmp_list1 ::= expr DUP_TOP ROT_THREE COMPARE_OP JUMP_IF_FALSE_OR_POP
                      cmp_list1 COME_FROM
        cmp_list1 ::= expr DUP_TOP ROT_THREE COMPARE_OP JUMP_IF_FALSE_OR_POP
                      cmp_list2 COME_FROM
        cmp_list2 ::= expr COMPARE_OP JUMP_FORWARD
        cmp_list2 ::= expr COMPARE_OP RETURN_VALUE

        exprlist ::= exprlist expr
        exprlist ::= expr

        nullexprlist ::=

        '''

    # MAKE_FUNCTION changed from Python 2 to Python 3.  In Python 2 it's
    # preceded only by the LOAD_CONST that contains the function code.  Since
    # Python 3.3, a second LOAD_CONST with the name of the function is added.
    #
    # Since generator expressions, dict comprehensions, set comprehensions and
    # lambdas use the MAKE_FUNCTION byte-code, we introduce a compatibility
    # layer in our grammar.  The following ``_py_load_*`` are overridden in
    # Python 3 with the second LOAD_CONST.  This way the rules for the bigger
    # structures remain stable across Python versions.
    #

    @override(_py_version < (3, 3))
    def p__py_loads(self, args):
        '''
        _py_load_genexpr   ::= LOAD_GENEXPR
        _py_load_lambda    ::= LOAD_LAMBDA
        _py_load_dictcomp  ::= LOAD_DICTCOMP
        _py_load_setcomp   ::= LOAD_SETCOMP
        '''

    @p__py_loads.override(_py_version >= (3, 3))
    def p__py_loads(self, args):
        '''
        _py_load_genexpr ::= LOAD_GENEXPR LOAD_CONST
        _py_load_lambda    ::= LOAD_LAMBDA LOAD_CONST
        _py_load_dictcomp  ::= LOAD_DICTCOMP LOAD_CONST
        _py_load_setcomp   ::= LOAD_SETCOMP LOAD_CONST
        '''

    @override(py3k)
    def p__py_load_listcomp(self, args):
        '''In Python 3.2+ list comprehensions are also wrapped
        inside a function.

        _py_load_listcomp ::= LOAD_LISTCOMP

        '''

    @p__py_load_listcomp.override(_py_version >= (3, 3))
    def p__py_load_listcomp(self, args):
        '''
        _py_load_listcomp ::= LOAD_LISTCOMP LOAD_CONST

        '''

    def p__comprehension(self, args):
        '''Common comprehension structure in Python 2.7

        _comprehension ::= MAKE_FUNCTION_0 _comp_iterarable
                           GET_ITER CALL_FUNCTION_1

        _comp_iterarable ::= expr

        comp_iter ::= comp_if
        comp_iter ::= comp_ifnot
        comp_iter ::= comp_for

        comp_iter ::= comp_body

        comp_body ::= set_comp_body
        comp_body ::= gen_comp_body
        comp_body ::= dict_comp_body

        set_comp_body ::= expr SET_ADD
        gen_comp_body ::= expr YIELD_VALUE POP_TOP
        dict_comp_body ::= expr expr MAP_ADD

        comp_if ::= expr jmp_false comp_iter
        comp_ifnot ::= expr jmp_true comp_iter
        comp_for ::= expr _for designator comp_iter JUMP_BACK

        '''

    @override(pypy)
    def p__comprehensions_changes_in_pypy(self, args):
        '''Alternative rules for Pypy.

        In Pypy we've seen the pattern of jumping forward the next comp_iter
        or jump back.

        comp_iter  ::= comp_ifnotor
        comp_iter  ::= comp_ifornot
        comp_ifnotor ::= expr jmp_false expr jmp_true JUMP_BACK comp_iter
        comp_ifnotor ::= expr jmp_true expr jmp_false JUMP_BACK comp_iter

        '''

    def p_setcomp_common(self, args):
        '''Set comprehensions.

        Common productions in all target Python versions.

        expr ::= setcomp
        stmt ::= setcomp_func
        setcomp_func ::= BUILD_SET_0 _comprehension_iter
                         FOR_ITER designator comp_iter
                         JUMP_BACK RETURN_VALUE RETURN_LAST

        setcomp ::= _py_load_setcomp _comprehension

        '''

    def p_list_comprehension_core(self, args):
        '''List comprehensions.

        This the core list comprehension stuff.  In Python 2 this will be
        inlined, but in Python 3 will be enclosed in a function.  See
        `p_list_comprehension` below.

        .. _rules:

        list_compr ::= BUILD_LIST_0 list_iter

        list_iter ::= list_for
        list_iter ::= list_if
        list_iter ::= list_if_not
        list_iter ::= lc_body

        list_for ::= expr _for designator list_iter JUMP_BACK
        list_if ::= expr jmp_false list_iter
        list_if_not ::= expr jmp_true list_iter

        lc_body ::= expr LIST_APPEND

        '''

    @override(py27)
    def p_list_comprehension(self, args):
        '''List comprehensions in Python 2.7 are 'exposed'.

        expr ::= list_compr

        '''

    @p_list_comprehension.override(py3k)
    def p_list_comprehension(self, args):
        '''List comprehensions in Python 3.

        Wrapped inside a function like the other comprehensions.

        list_compr_expr ::= _py_load_listcomp _comprehension

        expr ::= list_compr_expr
        stmt ::= list_compr

        '''

    @override(pypy)
    def p__pypy_listcomp(self, args):
        '''
        list_compr ::= expr BUILD_LIST_FROM_ARG _for designator list_iter
                       JUMP_BACK

        '''

    def p_genexpr(self, args):
        '''Generator expressions in Python 2.7.

        genexpr ::= _py_load_genexpr _comprehension

        expr ::= genexpr
        stmt ::= genexpr_func
        genexpr_func ::= _comprehension_iter FOR_ITER designator
                         comp_iter JUMP_BACK

        _comprehension_iter ::= LOAD_FAST

        '''

    def p_dictcomp(self, args):
        '''Dict comprehensions.

        dictcomp ::= _py_load_dictcomp _comprehension

        expr ::= dictcomp
        stmt ::= dictcomp_func

        dictcomp_func ::= BUILD_MAP _comprehension_iter
                          FOR_ITER designator
                          comp_iter JUMP_BACK RETURN_VALUE RETURN_LAST

        '''

    def p_grammar(self, args):
        '''The top-level grammar.

        sstmt ::= stmt
        sstmt ::= ifelsestmtr
        sstmt ::= return_stmt RETURN_LAST

        passstmt ::=

        lastc_stmt ::= iflaststmt
        lastc_stmt ::= whileelselaststmt
        lastc_stmt ::= forelselaststmt
        lastc_stmt ::= ifelsestmtr
        lastc_stmt ::= ifelsestmtc
        lastc_stmt ::= tryelsestmtc

        lastl_stmt ::= iflaststmtl
        lastl_stmt ::= ifelsestmtl
        lastl_stmt ::= forelselaststmtl
        lastl_stmt ::= tryelsestmtl

        designList ::= designator designator
        designList ::= designator DUP_TOP designList

        designator ::= STORE_FAST
        designator ::= STORE_NAME
        designator ::= STORE_GLOBAL
        designator ::= STORE_DEREF
        designator ::= expr STORE_ATTR
        designator ::= expr STORE_SLICE+0
        designator ::= expr expr STORE_SLICE+1
        designator ::= expr expr STORE_SLICE+2
        designator ::= expr expr expr STORE_SLICE+3
        designator ::= store_subscr
        designator ::= unpack
        designator ::= unpack_list

        store_subscr ::= expr expr STORE_SUBSCR

        stmt ::= return_lambda
        stmt ::= conditional_lambda

        stmt ::= return_stmt
        return_stmt ::= ret_expr RETURN_VALUE
        return_if_stmt ::= ret_expr RETURN_END_IF

        stmt ::= ifstmt
        _jump ::= JUMP_ABSOLUTE
        _jump ::= JUMP_FORWARD
        _jump ::= JUMP_BACK

        jmp_false    ::= POP_JUMP_IF_FALSE
        jmp_true    ::= POP_JUMP_IF_TRUE

        testexpr ::= testfalse
        testexpr ::= testtrue
        testfalse ::= expr jmp_false
        testtrue ::= expr jmp_true

        jmp_abs ::= JUMP_ABSOLUTE
        jmp_abs ::= JUMP_BACK

        _for ::= GET_ITER FOR_ITER
        _for ::= LOAD_CONST FOR_LOOP


        # `kwarg` is used by the customization engine when CALL_FUNCTION_* are
        # processed they are injected in the resultant `call_function` rule.
        kwarg   ::= LOAD_CONST expr

        '''

    def nonterminal(self, nt, args):
        collect = ('exprlist', 'kvlist', 'print_items')
        if nt in collect and len(args) > 1:
            #
            #  Collect iterated thingies together.
            #
            rv = args[0]
            rv.append(args[1])
        else:
            rv = GenericASTBuilder.nonterminal(self, nt, args)
        return rv

    def resolve(self, list):
        if len(list) == 2 and 'funcdef' in list and 'assign' in list:
            return 'funcdef'
        if 'grammar' in list and 'expr' in list:
            return 'expr'
        return GenericASTBuilder.resolve(self, list)


nop = lambda self, args: None


class Parser(object):
    def __init__(self):
        self.parser = _InternalParser()

    @property
    def customized(self):
        return self.parser.customized

    def add_rule(self, rule, operation):
        self.parser.addRule(rule, operation)

    def parse(self, tokens, customize):
        #
        #  Special handling for opcodes that take a variable number of
        #  arguments -- we add a new rule for each:
        #
        #    expr ::= {expr}^n BUILD_LIST_n
        #    expr ::= {expr}^n BUILD_TUPLE_n
        #
        #    unpack_list ::= UNPACK_LIST {expr}^n
        #    unpack ::= UNPACK_TUPLE {expr}^n
        #    unpack ::= UNPACK_SEQUENCE {expr}^n
        #
        #    mklambda ::= {expr}^n LOAD_LAMBDA MAKE_FUNCTION_n
        #    mklambda ::= {expr}^n load_closure LOAD_LAMBDA MAKE_FUNCTION_n
        #
        #    expr ::= expr {expr}^n CALL_FUNCTION_n
        #    expr ::= expr {expr}^n CALL_FUNCTION_VAR_n POP_TOP
        #    expr ::= expr {expr}^n CALL_FUNCTION_VAR_KW_n POP_TOP
        #    expr ::= expr {expr}^n CALL_FUNCTION_KW_n POP_TOP
        #
        from xoutil.eight import _py3
        for k, v in list(customize.items()):
            # avoid adding the same rule twice to this parser
            if k in self.customized:
                continue
            self.customized[k] = None
            op = k[:k.rfind('_')]
            if op in ('BUILD_LIST', 'BUILD_TUPLE', 'BUILD_SET'):
                rule = 'build_list ::= ' + 'expr '*v + k
            elif op in ('UNPACK_TUPLE', 'UNPACK_SEQUENCE'):
                rule = 'unpack ::= ' + k + ' designator'*v
            elif op == 'UNPACK_LIST':
                rule = 'unpack_list ::= ' + k + ' designator'*v
            elif op in ('DUP_TOPX', 'RAISE_VARARGS'):
                # no need to add a rule
                continue
            elif op == 'MAKE_FUNCTION':
                if _py3:
                    ndefaults = v & 0xFF
                    nkwonly = (v >> 8) & 0xFF
                    nannotations = (v >> 16) & 0x7FFF
                    assert nannotations == 0
                else:
                    ndefaults = v
                    nkwonly = 0
                self.add_rule(
                    'mklambda ::= %s %s _py_load_lambda %s' % (
                        'expr ' * ndefaults, 'kwarg ' * nkwonly, k),
                    nop
                )
                rule = None
            elif op == 'MAKE_CLOSURE':
                self.add_rule(
                    'mklambda ::= %s load_closure _py_load_lambda %s' % (
                        'expr '*v, k),
                    nop
                )
                self.add_rule(
                    'genexpr ::= %s load_closure _py_load_genexpr %s expr '
                    'GET_ITER CALL_FUNCTION_1' % ('expr '*v, k),
                    nop
                )
                self.add_rule(
                    'setcomp ::= %s load_closure _py_load_setcomp %s expr '
                    'GET_ITER CALL_FUNCTION_1' % ('expr '*v, k),
                    nop
                )
                self.add_rule(
                    'dictcomp ::= %s load_closure _py_load_dictcomp %s expr '
                    'GET_ITER CALL_FUNCTION_1' % ('expr '*v, k),
                    nop
                )
                if _py3:
                    # self.add_rule(
                    #     'list ::= %s load_closure _py_load_dictcomp %s expr '
                    #     'GET_ITER CALL_FUNCTION_1' % ('expr '*v, k),
                    #     nop
                    # )
                    pass
                rule = None
            elif op in ('CALL_FUNCTION', 'CALL_FUNCTION_VAR',
                        'CALL_FUNCTION_VAR_KW', 'CALL_FUNCTION_KW'):
                na = (v & 0xff)           # positional parameters
                nk = (v >> 8) & 0xff      # keyword parameters
                # number of apply equiv arguments:
                nak = (len(op) - len('CALL_FUNCTION')) // 3
                rule = 'call_function ::= expr ' + 'expr '*na + 'kwarg '*nk \
                       + 'expr ' * nak + k
            elif op == 'BUILD_SLICE':
                # since BUILD_SLICE can come in only two forms, it's already
                # embedded in our grammar, so just ignore it.
                rule = None
            else:
                raise Exception('unknown customize token %s' % k)
            if rule:
                self.add_rule(rule, nop)
        ast = self.parser.parse(tokens)
        return ast


def parse(tokens, customized):
    p = Parser()
    return p.parse(tokens, customized)

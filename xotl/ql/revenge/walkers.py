# -*- encoding: utf-8 -*-
# ---------------------------------------------------------------------
# xotl.ql.revenge.walkers
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
#

from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)

import sys
import re
import io

from types import CodeType
try:
    from types import EllipsisType, IntType
except ImportError:
    EllipsisType = type(Ellipsis)
    IntType = int

from .spark import GenericASTTraversal
from . import parsers, qst
from .parsers import AST
from .scanners import Token, Code

from .tools import pushto, take, pop_until_sentinel
from .tools import CODE_HAS_KWARG, CODE_HAS_VARARG

from .eight import py3k as _py3, _py_version


minint = -sys.maxsize-1

# Helper: decorators that push/take item to/from a stack.
take_n = lambda n: take(n, '_stack', 'children')
take_one = take_n(1)
take_two = take_n(2)
take_three = take_n(3)


def _ensure_compilable(astnode):
    if isinstance(astnode, qst.PyASTNode):
        attrs = getattr(astnode, '_attributes', [])
        if 'lineno' in attrs:
            astnode.lineno = 1
        if 'col_offset' in attrs:
            astnode.col_offset = 0
    return astnode


def pushtostack(f):
    @pushto('_stack')
    def inner(self, *args, **kw):
        return _ensure_compilable(f(self, *args, **kw))
    return inner


def pushsentinel(f, name=None):
    '''Decorator that pushes a sentinel to the stack.

    The sentinel will be pushed *after* the execution of the decorated
    function.

    '''
    def inner(self, node):
        sentinel = _build_sentinel(f, node, name)
        result = f(self, node)
        self._stack.append(sentinel)
        return result
    return inner


def take_until_sentinel(f, name=None):
    '''Decorator that pops items until it founds the proper sentinel.

    The decorated functions is expected to allow a keyword argument 'items'
    that will contain the items popped.

    '''
    def inner(self, node, **kwargs):
        sentinel = _build_sentinel(f, node, name)
        items = pop_until_sentinel(self._stack, sentinel)
        kwargs['items'] = items
        return f(self, node, **kwargs)
    return inner


def _build_sentinel(f, node, name=None):
    name = name if name else f.__name__
    if name.startswith('n_'):
        name = name[2:]
    elif name.startswith('_n_'):
        name = name[3:]
    if name.endswith('_exit'):
        name = name[:-5]
    return (name, node)


# Helper classes and metaclass for doing some like::
#
#   isinstance(node, ifsentence)

try:
    from xoutil.eight.meta import metaclass
except ImportError:
    from xoutil.objects import metaclass


class SentenceSyntaxType(type):
    def __instancecheck__(cls, instance):
        if isinstance(instance, (Token, AST)):
            checker = getattr(cls, 'checknode', None)
            if checker:
                return checker(instance)
        return False

    def __new__(cls, name, bases, attrs):
        checker = attrs.get('checknode', None)
        if checker and not isinstance(checker, classmethod):
            attrs['checknode'] = classmethod(checker)
        return super(SentenceSyntaxType, cls).__new__(cls, name, bases, attrs)

    def __call__(cls, node):
        return isinstance(node, cls)


class SyntaxElement(metaclass(SentenceSyntaxType)):
    def checknode(cls, node):
        return True


class Sentence(SyntaxElement):
    def checknode(cls, node):
        return node == 'stmt'


class Expression(SyntaxElement):
    def checknode(cls, node):
        return node == 'expr'


class Suite(SyntaxElement):
    def checknode(cls, node):
        return node == 'stmts'


class isifsentence(Sentence):
    def checknode(cls, node):
        try:
            return node == 'ifstmt' and node[1][0] == 'return_if_stmt'
        except (TypeError, IndexError):
            return False


# Some ASTs used for comparing code fragments (like 'return None' at
# the end of functions).
NONE = AST('ret_expr', [AST('expr', [AST('literal', [Token('LOAD_CONST',
                                                           argval=None)])])])

RETURN_NONE = AST('return_stmt', [NONE, Token('RETURN_VALUE')])


class QstBuilder(GenericASTTraversal, object):
    def __init__(self, ast=None):
        super(QstBuilder, self).__init__(ast)
        self._stack = []

    def stop(self, pop=True):
        assert len(self._stack) == 1
        if not pop:
            return self._stack[-1]
        else:
            return self._stack.pop()

    def peek(self):
        return self.stop(False)

    def _n_walk_innerfunc(islambda=True):
        def _walk_innerfunc(self, node):
            # This will push the body, the name of the arguments, the name of
            # the vararg (or None), and the name of the kwarg (or None) of the
            # qst.Lambda, the values of the `defaults` are to be complete by
            # the n_mklamdbda_exit.
            from . import Uncompyled
            # Notice the node[0], in Python 3.3+ node will have two items, the
            # LOAD_LAMBDA and the LOAD_CONST, previous versions won't have the
            # second.
            load_lambda = node[0]
            code = load_lambda.argval
            hasnone = 'None' in code.co_names
            uncompyled = Uncompyled(code, islambda=islambda, hasnone=hasnone)
            # XXX: uncompyled.qst will contain a qst.Expression, but we need
            # to keep only the body.
            self._stack.append(uncompyled.qst.body)
            # Argument names are the first of co_varnames
            argcount = code.co_argcount
            varnames = code.co_varnames
            args = [qst.Name(name, qst.Param()) for name in varnames[:argcount]]
            if CODE_HAS_VARARG(code):
                # This means the code uses the vararg and co_varnames contains
                # that name.
                vararg = varnames[argcount]
                argcount += 1
            else:
                vararg = None
            if CODE_HAS_KWARG(code):
                kwarg = varnames[argcount]
                argcount += 1
            else:
                kwarg = None
            self._stack.extend([args, vararg, kwarg])
            self.prune()
        return _walk_innerfunc

    @pushtostack
    def n_literal(self, node):
        def _build_qst(value):
            from numbers import Number
            from xoutil.eight import string_types
            if isinstance(value, string_types):
                cls = qst.Str
            elif isinstance(value, Number):
                cls = qst.Num
            else:
                # This is the case for folded constants like ``(1, 2)`` and
                # None, etc.  The QST to support this stuff.  Translators
                # might not.
                cls = lambda x: x
                if isinstance(value, list):
                    value = qst.List(
                        [_build_qst(v) for v in value],
                        qst.Load()
                    )
                elif isinstance(value, dict):
                    value = qst.Dict(
                        [_build_qst(k) for k in value],
                        [_build_qst(v) for v in value.values()]
                    )
                elif isinstance(value, tuple):
                    value = qst.Tuple(
                        [_build_qst(v) for v in value],
                        qst.Load()
                    )
                elif value is Ellipsis:
                    value = qst.Ellipsis()
                else:
                    # XXX: Sometime this is None and sometimes this must be
                    # qst.Name('None', qst.Load()), it depends on whether
                    # there's Name in the code object.  Or this is part of a
                    # slice.  Most of the time this the right choice is as a
                    # name, so slices must deal with this return value.
                    assert value is None
                    value = qst.Name('None', qst.Load())
            return _ensure_compilable(cls(value))

        load_const = self._ensure_child_token(node)
        value = load_const.argval
        return _build_qst(value)

    @pushtostack
    def n_identifier(self, node):
        load_name = self._ensure_child_token(node)
        return qst.Name(load_name.argval, qst.Load())

    n__comprehension_iter = n_identifier

    @pushtostack
    def n_STORE_FAST(self, node):
        assert isinstance(node, Token) and node.name.startswith('STORE_')
        return qst.Name(node.argval, qst.Store())
    n_STORE_NAME = n_STORE_GLOBAL = n_STORE_DEREF = n_STORE_FAST

    @pushsentinel
    def n_unpack(self, node):
        pass

    @pushtostack
    @take_until_sentinel
    def n_unpack_exit(self, node, children=None, items=None):
        return qst.Tuple(list(reversed(items)), qst.Load())

    @pushtostack
    @take_one
    def n_designator_exit(self, node, children=None):
        target, = children
        target.ctx = qst.Store()   # designators are stores
        return target

    @pushtostack
    def n_LOAD_ATTR(self, node):
        # When visiting a LOAD_ATTR just put the token on the stack,
        # `load_attr` will pick it and build the appropriate Attribute.
        assert isinstance(node, Token)
        return node

    @pushtostack
    @take_two
    def n_binary_subscr_exit(self, node, children=None):
        slice_, value = children
        # FIXME: This should be `qst.slice`.
        if not isinstance(slice_, qst.pyast.slice):
            # The slice may be already built for cases like ``a[s::st]`` where
            # the buildslice3 rule creates the `qst.Slice` object.
            slice_ = qst.Index(slice_)
        return qst.Subscript(value, slice_, qst.Load())

    @pushtostack
    @take_two
    def n_buildslice2_exit(self, node, children=None):
        upper, lower = children
        return qst.Slice(lower, upper, None)

    @pushtostack
    @take_one
    def n_slice0_exit(self, node, children=None):
        # This is ``obj[:]``
        obj, = children
        return qst.Subscript(obj, qst.Slice(None, None, None), qst.Load())

    @pushtostack
    @take_two
    def n_slice1_exit(self, node, children=None):
        # This is ``obj[lower:]``.
        lower, obj = children
        return qst.Subscript(obj, qst.Slice(lower, None, None), qst.Load())

    @pushtostack
    @take_two
    def n_slice2_exit(self, node, children=None):
        # This is ``obj[:upper]``.
        upper, obj = children
        return qst.Subscript(obj, qst.Slice(None, upper, None), qst.Load())

    @pushtostack
    @take_three
    def n_slice3_exit(self, node, children=None):
        # This is ``obj[lower:upper]``.
        upper, lower, obj = children
        return qst.Subscript(obj, qst.Slice(lower, upper, None), qst.Load())

    @pushtostack
    @take_three
    def n_buildslice3_exit(self, node, children=None):
        step, upper, lower = children
        return qst.Slice(lower, upper, step)

    @pushtostack
    @take_two
    def n_load_attr_exit(self, node, children=None):
        load_attr, obj = children
        assert isinstance(load_attr, Token)
        attr = load_attr.argval
        return qst.Attribute(obj, attr, qst.Load())

    @pushsentinel
    def n_call_function(self, node):
        # Mark the entrance to the function call, this will allows to retrieve
        # all the arguments. But first, push the number of positional
        # arguments and keyword arguments, so that we know how may items to
        # take from the stack
        callfunc = node[-1]
        assert isinstance(callfunc, Token) and \
            callfunc.name.startswith('CALL_FUNCTION_')
        name, val = callfunc.name.rsplit('_', 1)
        val = int(val)
        nargs = val & 0xFF
        nkwargs = (val >> 8) & 0xFF
        if name.endswith('_KW'):
            kwargs = 1
            name, _ = name.rsplit('_', 1)
        else:
            kwargs = None
        if name.endswith('_VAR'):
            starargs = 1
        else:
            starargs = None
        self._stack.append((nargs, nkwargs, starargs, kwargs))

    @pushtostack
    @take_until_sentinel
    def n_call_function_exit(self, node, children=None, items=None):
        nargs, nkwargs, starargs, kwarg = self._stack.pop()
        func = items.pop()
        args = []
        for _ in range(nargs):
            args.append(items.pop())
        kws = []
        for _ in range(nkwargs):
            kws.append(items.pop())
        if starargs:
            starargs = items.pop()
        if kwarg:
            kwarg = items.pop()
        assert not items
        return qst.Call(func, args, kws, starargs, kwarg)

    @pushtostack
    @take_one
    def n_kwarg_exit(self, node, children=None):
        token = node[0]
        value, = children
        # Since the name will be enclose in a qst.Name (per LOAD_CONST) we
        # need to unwrap it to build the `keyword`
        return qst.keyword(token.argval, value)

    @pushsentinel
    def n_mapexpr(self, node):
        pass

    @pushtostack
    @take_until_sentinel
    def n_mapexpr_exit(self, node, children=None, items=None):
        args = [], []  # keys, values
        # For {a: b, c: d}, items will be [c, d, a, b]... Reversed is [b, a,
        # d, c], so 0, 2, 4 ... are values, 1, 3, 5, ... are keys.
        for i, which in enumerate(reversed(items)):
            args[(i + 1) % 2].append(which)
        return qst.Dict(*args)

    # The _n_walk_innerfunc builds method that pushes the body of the inner
    # function for lambda and comprehensions.
    n__py_load_lambda = _n_walk_innerfunc(islambda=True)

    @pushsentinel
    def n_mklambda(self, node, children=None):
        _, argc = self._ensure_custom_tk(node, 'MAKE_FUNCTION')
        # Push both the amount of that will be in the stack the sentinel
        if _py3:
            defaults = argc & 0xFF
            nkwonly = (argc >> 8) & 0xFF
        else:
            defaults = argc
            nkwonly = 0
        self._stack.append((defaults, nkwonly))

    @pushtostack
    @take_until_sentinel
    def n_mklambda_exit(self, node, children=None, items=None):
        # Annotations are not possible (inlined) in lambdas, we don't bother.
        ndefaults, nkwonly = self._stack.pop()
        defaults = []
        for _ in range(ndefaults):
            defaults.append(_ensure_compilable(items.pop()))
        kwonly = []
        kwdefaults = []
        for i in range(nkwonly):
            kw = items.pop()   # we get a qst.keyword
            kwonly.append(_ensure_compilable(qst.arg(kw.arg, None)))
            kwdefaults.append(kw.value)
        body = items.pop()
        args = [_ensure_compilable(a) for a in items.pop()]
        vararg = items.pop()
        kwarg = items.pop()
        if _py3:
            # Recast args (they were qst.Name) as qst.arg in Python 3
            args = [_ensure_compilable(qst.arg(arg.id, None)) for arg in args]
            if _py_version < (3, 4):
                # Before Python 3,4 the vararg and kwarg were not enclosed
                # inside qst.arg and their annotations followed them in the
                # constructor.
                arguments = qst.arguments(args, vararg, None, kwonly, kwarg,
                                          None, defaults, kwdefaults)
            else:
                vararg = _ensure_compilable(qst.arg(vararg, None) if vararg else None)
                kwarg = _ensure_compilable(qst.arg(kwarg, None) if kwarg else None)
                arguments = qst.arguments(args, vararg, kwonly, kwdefaults,
                                          kwarg, defaults)
        else:
            arguments = qst.arguments(args, vararg, kwarg, defaults)
        return qst.Lambda(_ensure_compilable(arguments), body)

    _BINARY_OPS_QST_CLS = {
        'BINARY_ADD': qst.Add,
        'BINARY_MULTIPLY': qst.Mult,
        'BINARY_AND': qst.BitAnd,
        'BINARY_OR': qst.BitOr,
        'BINARY_XOR': qst.BitXor,
        'BINARY_SUBTRACT': qst.Sub,
        'BINARY_DIVIDE': qst.Div,
        'BINARY_TRUE_DIVIDE': qst.Div,
        'BINARY_FLOOR_DIVIDE': qst.FloorDiv,
        'BINARY_MODULO': qst.Mod,
        'BINARY_LSHIFT': qst.LShift,
        'BINARY_RSHIFT': qst.RShift,
        'BINARY_POWER': qst.Pow
    }

    @pushtostack
    def n_binary_op(self, node):
        code = self._ensure_child_token(node)
        cls = self._BINARY_OPS_QST_CLS[code.name]
        return cls()

    @pushtostack
    @take_three
    def n_binary_expr_exit(self, node, children=None):
        operation, right, left = children
        return qst.BinOp(left, operation, right)

    _UNARY_OPS_QST_CLS = {
        'UNARY_POSITIVE': qst.UAdd,
        'UNARY_NEGATIVE': qst.USub,
        'UNARY_INVERT': qst.Invert,
        'UNARY_NOT': qst.Not,
    }

    @pushtostack
    def n_unary_op(self, node):
        operator = self._ensure_child_token(node)
        return self._UNARY_OPS_QST_CLS[operator.name]()

    n___unary_not = n_unary_op

    @pushtostack
    @take_two
    def n_unary_expr_exit(self, node, children=None):
        op, operand = children
        return qst.UnaryOp(op, operand)

    n_unary_not_exit = n_unary_expr_exit

    _COMPARE_OPS_QST_CLS = {
        'in': qst.In,
        'not in': qst.NotIn,
        'is': qst.Is,
        'is not': qst.IsNot,
        '==': qst.Eq,
        '!=': qst.NotEq,
        '<': qst.Lt,
        '<=': qst.LtE,
        '>': qst.Gt,
        '>=': qst.GtE,
    }
    _COMPARE_OPS_QST_CLS_VALS = tuple(_COMPARE_OPS_QST_CLS.values())

    @pushtostack
    def n_COMPARE_OP(self, node):
        return self._COMPARE_OPS_QST_CLS[node.argval]()

    def n_cmp_list(self, node):
        # Push a mark to the stack to know when to stop when building the list
        # when exiting the node.  See `n_cmp_list_exit` method
        self._stack.append(('cmp_list', node))

    @pushtostack
    def n_cmp_list_exit(self, node, children=None):
        from .tools import split
        sentinel = ('cmp_list', node)
        items = pop_until_sentinel(self._stack, sentinel)
        left = items.pop()  # The last item is the first.
        # Then, in reversed stack other we'll have compare operators and the
        # other operands.
        cmpops, others = split(
            reversed(items),
            lambda item: isinstance(item, self._COMPARE_OPS_QST_CLS_VALS)
        )
        return qst.Compare(left, cmpops, others)

    @pushtostack
    @take_three
    def n_compare_exit(self, node, children=None):
        cmpop, right, left = children
        return qst.Compare(left, [cmpop], [right])

    # Notice we should build a qst.Expression at the exit of every `expr`
    # since that would (re)create the concrete syntax (for instance, that
    # would make the left and right operands of binary operators instances of
    # qst.Expression).  We only build the Expression at the last moment.
    @pushtostack
    @take_one
    def n_ret_expr_exit(self, node, children=None):
        body = children[0]
        return qst.Expression(body)

    @pushtostack
    @take_three
    def n_conditional_exit(self, node, children=None):
        orelse, body, test = children
        return qst.IfExp(test, body, orelse)

    @pushtostack
    @take_two
    def n_and_exit(self, node, children=None):
        right, left = children
        # Since BoolOps are 'collapsible': a and b and c collapse into a
        # single BoolOp
        if isinstance(right, qst.pyast.BoolOp) and isinstance(right.op, qst.pyast.And):
            # collapse
            right.values[0:0] = [left]
            return right
        else:
            return qst.BoolOp(qst.And(), [left, right])

    @pushtostack
    @take_two
    def n_or_exit(self, node, children=None):
        right, left = children
        # Since BoolOps are 'collapsible': a or b or c collapse into a
        # single BoolOp
        if isinstance(right, qst.pyast.BoolOp) and isinstance(right.op, qst.pyast.Or):
            # collapse
            right.values[0:0] = [left]
            return right
        else:
            return qst.BoolOp(qst.Or(), [left, right])

    # This pushes the inner body, args, vararg, kwonly, kwdefaults, and kwarg
    # to the stack, there's no defaults to be retrieved from the stack.
    n__py_load_genexpr = _n_walk_innerfunc(islambda=False)

    @pushsentinel
    def n_genexpr(self, node):
        pass

    @pushtostack
    @take_until_sentinel
    def n_genexpr_exit(self, node, children=None, items=None):
        # The `item` will be ``[iterable, ...., qst.GeneratorExp]``, the space
        # in between is the 'inner function' arg, vararg, etc...  We can
        # safely ignore all function related args, since we're not going to
        # produce a function definition.
        #
        # But the qst.GeneratorExp will have its first comprehesion with the
        # wrong iterable, replace it.
        iterable = items.pop(0)
        genexpr = items.pop()
        genexpr.generators[0].iter = iterable
        return genexpr

    @pushsentinel
    def n_genexpr_func(self, node):
        pass

    # The comprehension stuff.
    #
    # Since `comp_if` may deeply nested and intertwined with comp_ifnot,
    # comp_for, but with a single comp_body at the very end, we simply need to
    # collect all the expressions inside the `comp_iter` and push the new if
    # expression to the stack.  But this is the default, the milestones are
    # comp_for and the top-level comprehension.  The `comp_ifnot` needs
    # rewriting cause the 'expr' needs to be negated.
    #
    @pushtostack
    @take_until_sentinel
    def n_genexpr_func_exit(self, node, children=None, items=None):
        # At this point we should at least three items in the stack.  `items`
        # will be: [elt, ...., target, iterable].
        #
        # The items in between may be partially constructed
        # `qst.comprehension` (the result of comp_for)
        eltmark, elt = items.pop(0)
        assert isinstance(eltmark, tuple) and eltmark[0] == 'elt'
        iterable = _ensure_compilable(items.pop())
        assert getattr(iterable, 'id', '').startswith('.')
        target = _ensure_compilable(items.pop())
        ifs = []
        while items and not isinstance(items[-1], qst.pyast.comprehension):
            item = items.pop()
            ifs.append(_ensure_compilable(item))
        comprehensions = list(reversed(items)) if items else []
        comprehensions.insert(0, _ensure_compilable(
            qst.comprehension(target, iterable, ifs)
        ))
        # XXX: Wrap it in an Expression since it will be unwrapped by
        # _walk_innerfunc
        return qst.Expression(_ensure_compilable(
            qst.GeneratorExp(elt, comprehensions)
        ))

    @pushsentinel
    def n_comp_for(self, node):
        pass

    @take_until_sentinel
    def n_comp_for_exit(self, node, children=None, items=None):
        # At this point the items should be [elt, .... , designator, iterable]
        # just like at the top level generator... the items in between are
        # conditions or other comprehensions we should leave.
        iterable = _ensure_compilable(items.pop())
        target = _ensure_compilable(items.pop())
        ifs = []
        # items should have more than one item to have any ifs or
        # inner generators.
        while len(items) > 1 and not isinstance(items[-1], qst.pyast.comprehension):
            ifs.append(_ensure_compilable(items.pop()))
        self._stack.append(_ensure_compilable(
            qst.comprehension(target, iterable, ifs)
        ))
        for which in reversed(items):
            self._stack.append(which)

    @pushsentinel
    def n_comp_if(self, node):
        pass

    @take_until_sentinel
    def n_comp_if_exit(self, node, children=None, items=None):
        self._stack.extend(reversed(items))

    @pushsentinel
    def n_comp_ifnot(self, node):
        # We need to mark this cause we must negate the result.
        pass

    @take_until_sentinel
    def n_comp_ifnot_exit(self, node, children=None, items=None):
        # comp_ifnot ::= expr jmp_true comp_iter, we must negate the first
        # 'expr' but leave others as is.  Since `items` is the
        # stack-pop-order, i.e ``[...., expr]`` we need to inserted them in
        # the reverse order.
        for index, item in enumerate(reversed(items)):
            if index == 0:
                item = qst.UnaryOp(qst.Not(), item)
            self._stack.append(item)

    @pushtostack
    @take_one
    def n_comp_body_exit(self, node, children=None):
        elt, = children
        return (('elt', node), elt)

    @pushsentinel
    def n_build_list(self, node):
        pass

    @pushtostack
    @take_until_sentinel
    def n_build_list_exit(self, node, children=None, items=None):
        opcode, nitems = self._ensure_custom_tk(
            node, ('BUILD_LIST', 'BUILD_SET', 'BUILD_TUPLE')
        )
        if opcode == 'BUILD_LIST':
            cls = qst.List
            args = (qst.Load(), )
        elif opcode == 'BUILD_SET':
            cls = qst.Set
            args = ()
        else:
            assert opcode == 'BUILD_TUPLE'
            cls = qst.Tuple
            args = (qst.Load(), )
        return cls(list(reversed(items)), *args)

    def _ensure_single_child(self, node, msg='%s must have a single child'):
        if '%s' in msg:
            name = self._find_name()
            msg = msg % name
        assert len(node) == 1
        return node[0]

    def _ensure_child_token(self, node, msg='%s must have single token child'):
        if '%s' in msg:
            name = self._find_name()
            msg = msg % name
        res = self._ensure_single_child(node, msg)
        assert isinstance(res, Token), msg
        return res

    def _ensure_custom_tk(self, node, prefixes):
        tk = node[-1]
        assert isinstance(tk, Token)
        if not isinstance(prefixes, (list, tuple)):
            prefixes = [prefixes, ]
        found = next(
            (tk.name.rsplit('_', 1) for prefix in prefixes
             if tk.name.rsplit('_', 1)[0] == prefix),
            None
        )
        if found:
            opcode, custom = found
            return opcode, int(custom)
        else:
            assert False

    def _find_name(self):
        res = None
        depth = 0
        try:
            f = sys._getframe(3)
        except:
            f = None
        try:
            while f is not None and res is None and depth < 4:
                name = f.f_code.co_name
                if name and name.startswith('n_'):
                    res = name
                depth += 1
                f = f.f_back
            return res if res else 'This node'
        except:
            return 'This node'
        finally:
            f = None

    @staticmethod
    def build_ast(tokens, customize, **kwargs):
        '''Build the AST for the tokens and customizations provided.

        If the tokens are the code of a lambda function you should make

        :keyword islambda: Indicates this is the definition code of a lambda.
        :keyword isLambda: Deprecrated alias for `islambda`.

        :keyword hasnone: Indicate that None appears as a name.  Usually not
                          needed since we inspect it.
        :keyword noneInNames: Deprecated alias for `hasnone`.

        '''
        from xoutil import Unset
        islambda = kwargs.pop('islambda', Unset)
        if islambda is Unset:
            islambda = kwargs.pop('isLambda', Unset)
        hasnone = kwargs.pop('hasnone', Unset)
        if hasnone is Unset:
            hasnone = kwargs.pop('noneInNames', Unset)
        if islambda:
            tokens.append(Token('LAMBDA_MARKER'))
        elif len(tokens) > 2 or (len(tokens) == 2 and not hasnone):
            if tokens[-1] == Token('RETURN_VALUE'):
                if tokens[-2] == Token('LOAD_CONST'):
                    del tokens[-2:]
                else:
                    tokens.append(Token('RETURN_LAST'))
        if len(tokens) == 0:
            # This is probably a LOAD_CONST None RETURN_VALUE that was
            # suppressed in Python 3.4 and Pypy.
            return RETURN_NONE
        ast = parsers.parse(tokens, customize)
        return ast


#  Decompilation (walking AST)
#
#  All table-driven.  Step 1 determines a table (T) and a path to a
#  table key (K) from the node type (N) (other nodes are shown as O):
#
#         N                  N               N=K
#     / | ... \          / | ... \        / | ... \
#    O  O      O        O  O      K      O  O      O
#              |
#              K
#
#  MAP_R0 (TABLE_R0)  MAP_R (TABLE_R)  MAP_DIRECT (TABLE_DIRECT)
#
#  The default is a direct mapping.  The key K is then extracted from the
#  subtree and used to find a table entry T[K], if any.  The result is a
#  format string and arguments (a la printf()) for the formatting engine.
#  Escapes in the format string are:
#
#       %c      evaluate N[A] recursively*
#       %C      evaluate N[A[0]]..N[A[1]-1] recursively, separate by A[2]*
#
#       %p and %P  are the same as %c and %C but preserving the precedence value.
#
#       %,      print ',' if last %C only printed one item (for tuples--unused)
#       %|      tab to current indentation level
#       %+      increase current indentation level
#       %-      decrease current indentation level
#       %{...}  evaluate ... in context of N
#       %%      literal '%'
#
#  * indicates an argument (A) required.
#
#  The '%' may optionally be followed by a number (C) in square brackets,
#  which makes the engine walk down to N[C] before evaluating the escape code.
#

TAB = ' ' * 4   # is less spacy than "\t"
INDENT_PER_LEVEL = ' '  # additional intent per pretty-print level

TABLE_R = {
    'POP_TOP':          ('%|%c\n', 0),
    'STORE_ATTR':       ('%c.%[1]{argval}', 0),
    'STORE_SLICE+0':    ('%c[:]', 0),
    'STORE_SLICE+1':    ('%c[%p:]', 0, (1, 100)),
    'STORE_SLICE+2':    ('%c[:%p]', 0, (1, 100)),
    'STORE_SLICE+3':    ('%c[%p:%p]', 0, (1, 100), (2, 100)),
    'DELETE_SLICE+0':   ('%|del %c[:]\n', 0),
    'DELETE_SLICE+1':   ('%|del %c[%c:]\n', 0, 1),
    'DELETE_SLICE+2':   ('%|del %c[:%c]\n', 0, 1),
    'DELETE_SLICE+3':   ('%|del %c[%c:%c]\n', 0, 1, 2),
    'DELETE_ATTR':      ('%|del %c.%[-1]{argval}\n', 0),
}

TABLE_R0 = {
    #    'BUILD_LIST':      ('[%C]',      (0,-1,', ') ),
    #    'BUILD_TUPLE':     ('(%C)',      (0,-1,', ') ),
    #    'CALL_FUNCTION':   ('%c(%C)', 0, (1,-1,', ') ),
}

TABLE_DIRECT = {
    'BINARY_ADD': ('+',),
    'BINARY_SUBTRACT': ('-',),
    'BINARY_MULTIPLY': ('*',),
    'BINARY_DIVIDE': ('/',),
    'BINARY_TRUE_DIVIDE': ('/',),
    'BINARY_FLOOR_DIVIDE': ('//',),
    'BINARY_MODULO': ('%%',),
    'BINARY_POWER': ('**',),
    'BINARY_LSHIFT': ('<<',),
    'BINARY_RSHIFT': ('>>',),
    'BINARY_AND': ('&',),
    'BINARY_OR': ('|',),
    'BINARY_XOR': ('^',),

    # binary_expr ::= expr expr binary_op
    'binary_expr': ('%c %c %c', 0, -1, 1),


    'INPLACE_ADD': ('+=',),
    'INPLACE_SUBTRACT': ('-=',),
    'INPLACE_MULTIPLY': ('*=',),
    'INPLACE_DIVIDE': ('/=',),
    'INPLACE_TRUE_DIVIDE': ('/=',),
    'INPLACE_FLOOR_DIVIDE': ('//=',),
    'INPLACE_MODULO': ('%%=',),
    'INPLACE_POWER': ('**=',),
    'INPLACE_LSHIFT': ('<<=',),
    'INPLACE_RSHIFT': ('>>=',),
    'INPLACE_AND': ('&=',),
    'INPLACE_OR': ('|=',),
    'INPLACE_XOR': ('^=',),

    'UNARY_POSITIVE': ('+',),
    'UNARY_NEGATIVE': ('-',),
    'UNARY_INVERT': ('~%c'),
    'unary_expr': ('%c%c', 1, 0),

    'unary_not': ('not %c', 0),
    'unary_convert': ('`%c`', 0),
    'get_iter': ('iter(%c)', 0),
    'slice0': ('%c[:]', 0),
    'slice1': ('%c[%p:]', 0, (1, 100)),
    'slice2': ('%c[:%p]', 0, (1, 100)),
    'slice3': ('%c[%p:%p]', 0, (1, 100), (2, 100)),

    'IMPORT_FROM': ('%{argval}', ),

    'load_attr': ('%c.%[1]{argval}', 0),

    'LOAD_FAST': ('%{argval}', ),
    'LOAD_NAME': ('%{argval}', ),
    'LOAD_GLOBAL': ('%{argval}', ),
    'LOAD_DEREF': ('%{argval}', ),
    'LOAD_LOCALS': ('locals()', ),
    'LOAD_ASSERT': ('%{argval}', ),

    'DELETE_FAST': ('%|del %{argval}\n', ),
    'DELETE_NAME': ('%|del %{argval}\n', ),
    'DELETE_GLOBAL': ('%|del %{argval}\n', ),
    'delete_subscr': ('%|del %c[%c]\n', 0, 1,),
    'binary_subscr': ('%c[%p]', 0, (1, 100)),
    'binary_subscr2': ('%c[%p]', 0, (1, 100)),
    'store_subscr': ('%c[%c]', 0, 1),
    'STORE_FAST': ('%{argval}', ),
    'STORE_NAME': ('%{argval}', ),
    'STORE_GLOBAL': ('%{argval}', ),
    'STORE_DEREF': ('%{argval}', ),
    'unpack': ('%C%,', (1, sys.maxsize, ', ')),
    'unpack_w_parens': ('(%C%,)', (1, sys.maxsize, ', ')),
    'unpack_list': ('[%C]', (1, sys.maxsize, ', ')),
    'build_tuple2': ('%P', (0, -1, ', ', 100)),

    'list_iter': ('%c', 0),
    'list_for': (' for %c in %c%c', 2, 0, 3),
    'list_if': (' if %c%c', 0, 2),
    'list_if_not': (' if not %p%c', (0, 22), 2),
    'lc_body': ('',),        # ignore when recusing

    'comp_iter': ('%c', 0),
    'comp_for': (' for %c in %c%c', 2, 0, 3),
    'comp_if': (' if %c%c', 0, 2),
    'comp_ifnot': (' if not %p%c', (0, 22), 2),
    'comp_body': ('',),        # ignore when recusing
    'set_comp_body': ('%c', 0),
    'gen_comp_body': ('%c', 0),
    'dict_comp_body': ('%c: %c', 1, 0),

    'assign': ('%|%c = %p\n', -1, (0, 200)),
    'augassign1': ('%|%c %c %c\n', 0, 2, 1),
    'augassign2': ('%|%c.%[2]{argval} %c %c\n', 0, -3, -4),

    'designList': ('%c = %c', 0, -1),
    'and': ('%c and %c', 0, 2),
    'ret_and': ('%c and %c', 0, 2),
    'and2': ('%c', 3),
    'or': ('%c or %c', 0, 2),
    'ret_or': ('%c or %c', 0, 2),
    'conditional': ('%p if %p else %p', (2, 27), (0, 27), (4, 27)),
    'ret_cond': ('%p if %p else %p', (2, 27), (0, 27), (4, 27)),
    'conditionalnot': ('%p if not %p else %p', (2, 27), (0, 22), (4, 27)),
    'ret_cond_not': ('%p if not %p else %p', (2, 27), (0, 22), (4, 27)),
    'conditional_lambda': ('(%c if %c else %c)', 2, 0, 3),
    'return_lambda': ('%c', 0),
    'compare': ('%p %[-1]{argval} %p', (0, 19), (1, 19)),
    'cmp_list': ('%p %p', (0, 20), (1, 19)),
    'cmp_list1': ('%[3]{argval} %p %p', (0, 19), (-2, 19)),
    'cmp_list2': ('%[1]{argval} %p', (0, 19)),

    'funcdef': ('\n\n%|def %c\n', -2),  # -2 to handle closures
    'funcdefdeco': ('\n\n%c', 0),
    'mkfuncdeco': ('%|@%c\n%c', 0, 1),
    'mkfuncdeco0': ('%|def %c\n', 0),
    'classdefdeco': ('%c', 0),
    'classdefdeco1': ('\n\n%|@%c%c', 0, 1),
    'kwarg': ('%[0]{argval}=%c', 1),
    'importlist2': ('%C', (0, sys.maxsize, ', ')),

    'assert': ('%|assert %c\n', 0),
    'assert2': ('%|assert %c, %c\n', 0, 3),
    'assert_expr_or': ('%c or %c', 0, 2),
    'assert_expr_and': ('%c and %c', 0, 2),
    'print_items_stmt': ('%|print %c%c,\n', 0, 2),
    'print_items_nl_stmt': ('%|print %c%c\n', 0, 2),
    'print_item': (', %c', 0),
    'print_nl': ('%|print\n', ),
    'print_to': ('%|print >> %c, %c,\n', 0, 1),
    'print_to_nl': ('%|print >> %c, %c\n', 0, 1),
    'print_nl_to': ('%|print >> %c\n', 0),
    'print_to_items': ('%C', (0, 2, ', ')),

    'call_stmt': ('%|%p\n', (0, 200)),
    'break_stmt': ('%|break\n',),
    'continue_stmt': ('%|continue\n',),

    'raise_stmt0': ('%|raise\n',),
    'raise_stmt1': ('%|raise %c\n', 0),
    'raise_stmt2': ('%|raise %c, %c\n', 0, 1),
    'raise_stmt3': ('%|raise %c, %c, %c\n', 0, 1, 2),

    'ifstmt': ('%|if %c:\n%+%c%-', 0, 1),
    'iflaststmt': ('%|if %c:\n%+%c%-', 0, 1),
    'iflaststmtl': ('%|if %c:\n%+%c%-', 0, 1),
    'testtrue': ('not %p', (0, 22)),

    'ifelsestmt': ('%|if %c:\n%+%c%-%|else:\n%+%c%-', 0, 1, 3),
    'ifelsestmtc': ('%|if %c:\n%+%c%-%|else:\n%+%c%-', 0, 1, 3),
    'ifelsestmtl': ('%|if %c:\n%+%c%-%|else:\n%+%c%-', 0, 1, 3),
    'ifelifstmt': ('%|if %c:\n%+%c%-%c', 0, 1, 3),
    'elifelifstmt': ('%|elif %c:\n%+%c%-%c', 0, 1, 3),
    'elifstmt': ('%|elif %c:\n%+%c%-', 0, 1),
    'elifelsestmt': ('%|elif %c:\n%+%c%-%|else:\n%+%c%-', 0, 1, 3),
    'ifelsestmtr': ('%|if %c:\n%+%c%-%|else:\n%+%c%-', 0, 1, 2),
    'elifelsestmtr': ('%|elif %c:\n%+%c%-%|else:\n%+%c%-\n\n', 0, 1, 2),

    'whilestmt': ('%|while %c:\n%+%c%-\n\n', 1, 2),
    'while1stmt': ('%|while 1:\n%+%c%-\n\n', 1),
    'while1elsestmt': ('%|while 1:\n%+%c%-%|else:\n%+%c%-\n\n', 1, 3),
    'whileelsestmt': ('%|while %c:\n%+%c%-%|else:\n%+%c%-\n\n', 1, 2, -2),
    'whileelselaststmt': ('%|while %c:\n%+%c%-%|else:\n%+%c%-', 1, 2, -2),
    'forstmt': ('%|for %c in %c:\n%+%c%-\n\n', 3, 1, 4),
    'forelsestmt': (
        '%|for %c in %c:\n%+%c%-%|else:\n%+%c%-\n\n', 3, 1, 4, -2),
    'forelselaststmt': (
        '%|for %c in %c:\n%+%c%-%|else:\n%+%c%-', 3, 1, 4, -2),
    'forelselaststmtl': (
        '%|for %c in %c:\n%+%c%-%|else:\n%+%c%-\n\n', 3, 1, 4, -2),
    'trystmt': ('%|try:\n%+%c%-%c\n\n', 1, 3),
    'tryelsestmt': ('%|try:\n%+%c%-%c%|else:\n%+%c%-\n\n', 1, 3, 4),
    'tryelsestmtc': ('%|try:\n%+%c%-%c%|else:\n%+%c%-', 1, 3, 4),
    'tryelsestmtl': ('%|try:\n%+%c%-%c%|else:\n%+%c%-', 1, 3, 4),
    'tf_trystmt': ('%c%-%c%+', 1, 3),
    'tf_tryelsestmt': ('%c%-%c%|else:\n%+%c', 1, 3, 4),
    'except': ('%|except:\n%+%c%-', 3),
    'except_cond1': ('%|except %c:\n', 1),
    'except_cond2': ('%|except %c as %c:\n', 1, 5),
    'except_suite': ('%+%c%-%C', 0, (1, sys.maxsize, '')),
    'tryfinallystmt': ('%|try:\n%+%c%-%|finally:\n%+%c%-\n\n', 1, 5),
    'withstmt': ('%|with %c:\n%+%c%-', 0, 3),
    'withasstmt': ('%|with %c as %c:\n%+%c%-', 0, 2, 3),
    'passstmt': ('%|pass\n',),
    'STORE_FAST': ('%{argval}',),
    'kv': ('%c: %c', 3, 1),
    'kv2': ('%c: %c', 1, 2),
    'mapexpr': ('{%[1]C}', (0, sys.maxsize, ', ')),

    # Python 2.5 Additions

    # Import style for 2.5
    'importstmt': ('%|import %c\n', 2),
    'importstar': ('%|from %[2]{argval} import *\n',),
    'importfrom': ('%|from %[2]{argval} import %c\n', 3),
    'importmultiple': ('%|import %c%c\n', 2, 3),
    'import_cont': (', %c', 2),

    # CE - Fixes for tuples
    'assign2': ('%|%c, %c = %c, %c\n', 3, 4, 0, 1),
    'assign3': ('%|%c, %c, %c = %c, %c, %c\n', 5, 6, 7, 0, 1, 2),
}


MAP_DIRECT = (TABLE_DIRECT, )
MAP_R0 = (TABLE_R0, -1, 0)
MAP_R = (TABLE_R, -1)

MAP = {
    'stmt':             MAP_R,
    'call_function':    MAP_R,
    'del_stmt':         MAP_R,
    'designator':       MAP_R,
    'exprlist':         MAP_R0,
}

PRECEDENCE = {
    'build_list': 0,
    'mapexpr': 0,
    'unary_convert': 0,
    'dictcomp': 0,
    'setcomp': 0,
    'list_compr': 0,
    'genexpr': 0,

    'load_attr': 2,
    'binary_subscr': 2,
    'binary_subscr2': 2,
    'slice0': 2,
    'slice1': 2,
    'slice2': 2,
    'slice3': 2,
    'buildslice2': 2,
    'buildslice3': 2,
    'call_function': 2,

    'BINARY_POWER': 4,

    'unary_expr': 6,

    'BINARY_MULTIPLY': 8,
    'BINARY_DIVIDE': 8,
    'BINARY_TRUE_DIVIDE': 8,
    'BINARY_FLOOR_DIVIDE': 8,
    'BINARY_MODULO': 8,

    'BINARY_ADD': 10,
    'BINARY_SUBTRACT': 10,

    'BINARY_LSHIFT': 12,
    'BINARY_RSHIFT': 12,

    'BINARY_AND': 14,

    'BINARY_XOR': 16,

    'BINARY_OR': 18,

    'cmp': 20,

    'unary_not': 22,

    'and': 24,
    'ret_and': 24,

    'or': 26,
    'ret_or': 26,

    'conditional': 28,
    'conditionalnot': 28,
    'ret_cond': 28,
    'ret_cond_not': 28,

    '_mklambda': 30,
    'yield': 101
}

ASSIGN_TUPLE_PARAM = lambda param_name: AST('expr',
                                            [Token('LOAD_FAST',
                                                   argval=param_name)])

#
escape = re.compile(
    r'''
    (?P<prefix>[^%]*)%(\[ (?P<child> -? \d+ ) \])?
    ((?P<type>[^{]) | ([{] (?P<expr> [^}]*)[}]))
''', re.VERBOSE)


class ParserError(parsers.ParserError):
    def __init__(self, error, tokens):
        # FIXME: Should we use PEP 3134 __cause__ or __context__?
        self.error = error  # previous exception
        self.tokens = tokens

    def __str__(self):
        lines = ['--- This code section failed: ---']
        lines.extend(map(str, self.tokens))
        lines.extend(['', str(self.error)])
        return '\n'.join(lines)


def find_globals(node, globs):
    """Find globals in this statement."""
    for n in node:
        if isinstance(n, AST):
            globs = find_globals(n, globs)
        elif n.name in ('STORE_GLOBAL', 'DELETE_GLOBAL'):
            globs.add(n.argval)
    return globs


def find_all_globals(node, globs):
    """Find globals in this statement."""
    for n in node:
        if isinstance(n, AST):
            globs = find_all_globals(n, globs)
        elif n.name in ('STORE_GLOBAL', 'DELETE_GLOBAL', 'LOAD_GLOBAL'):
            globs.add(n.argval)
    return globs


def find_none(node):
    for n in node:
        if isinstance(n, AST):
            if not (n == 'return_stmt' or n == 'return_if_stmt'):
                if find_none(n):
                    return True
        elif n.name == 'LOAD_CONST' and n.argval is None:
            return True
    return False


class Walker(QstBuilder):
    stacked_params = ('f', 'indent', 'isLambda', '_globals')

    def __init__(self, scanner):
        import io
        GenericASTTraversal.__init__(self, ast=None)
        self.scanner = scanner
        out = io.BytesIO()
        params = {
            'f': out,
            'indent': '',
            }
        self._params = params
        self._param_stack = []
        self.ERROR = None
        self.prec = 100
        self.return_none = False
        self.mod_globs = set()
        self.currentclass = None
        self.pending_newlines = 0

    f = property(lambda s: s._params['f'],
                 lambda s, x: s._params.__setitem__('f', x),
                 lambda s: s._params.__delitem__('f'),
                 None)

    indent = property(lambda s: s._params['indent'],
                      lambda s, x: s._params.__setitem__('indent', x),
                      lambda s: s._params.__delitem__('indent'),
                      None)

    isLambda = property(lambda s: s._params['isLambda'],
                        lambda s, x: s._params.__setitem__('isLambda', x),
                        lambda s: s._params.__delitem__('isLambda'),
                        None)

    _globals = property(lambda s: s._params['_globals'],
                        lambda s, x: s._params.__setitem__('_globals', x),
                        lambda s: s._params.__delitem__('_globals'),
                        None)

    def indentMore(self, indent=TAB):
        self.indent += indent

    def indentLess(self, indent=TAB):
        self.indent = self.indent[:-len(indent)]

    def traverse(self, node, indent=None, isLambda=0):
        self._param_stack.append(self._params)
        if indent is None:
            indent = self.indent
        p = self.pending_newlines
        self.pending_newlines = 0
        self._params = {
            '_globals': {},
            'f': io.BytesIO(),
            'indent': indent,
            'isLambda': isLambda,
            }
        self.preorder(node)
        self.f.write('\n'*self.pending_newlines)
        result = self.f.getvalue()
        self._params = self._param_stack.pop()
        self.pending_newlines = p
        return result

    def write(self, *data):
        if (len(data) == 0) or (len(data) == 1 and data[0] == ''):
            return
        out = ''.join((str(j) for j in data))
        n = 0
        for i in out:
            if i == '\n':
                n += 1
                if n == len(out):
                    self.pending_newlines = max(self.pending_newlines, n)
                    return
            elif n:
                self.pending_newlines = max(self.pending_newlines, n)
                out = out[n:]
                break
            else:
                break

        if self.pending_newlines > 0:
            self.f.write('\n'*self.pending_newlines)
            self.pending_newlines = 0

        for i in out[::-1]:
            if i == '\n':
                self.pending_newlines += 1
            else:
                break

        if self.pending_newlines:
            out = out[:-self.pending_newlines]
        self.f.write(out)

    def print_(self, *data):
        if data and not(len(data) == 1 and data[0] == ''):
            self.write(*data)
        self.pending_newlines = max(self.pending_newlines, 1)

    def print_docstring(self, indent, docstring):
        from xoutil.eight import text_type
        quote = '"""'
        self.write(indent)
        # TODO: Verify
        if type(docstring) == text_type:
            self.write('u')
            docstring = repr(docstring.expandtabs())[2:-1]
        else:
            docstring = repr(docstring.expandtabs())[1:-1]

        for (orig, replace) in (('\\\\', '\t'),
                                ('\\r\\n', '\n'),
                                ('\\n', '\n'),
                                ('\\r', '\n'),
                                ('\\"', '"'),
                                ("\\'", "'")):
            docstring = docstring.replace(orig, replace)

        # Do a raw string if there are backslashes but no other escaped
        # characters: also check some edge cases
        if ('\t' in docstring
            and '\\' not in docstring
            and len(docstring) >= 2
            and docstring[-1] != '\t'
            and (docstring[-1] != '"'
                 or docstring[-2] == '\t')):
            self.write('r')  # raw string
            # restore backslashes unescaped since raw
            docstring = docstring.replace('\t', '\\')
        else:
            # Escape '"' if it's the last character, so it doesn't ruin the
            # ending triple quote
            if len(docstring) and docstring[-1] == '"':
                docstring = docstring[:-1] + '\\"'
            # Escape triple quote anywhere
            docstring = docstring.replace('"""', '\\"\\"\\"')
            # Restore escaped backslashes
            docstring = docstring.replace('\t', '\\\\')
        lines = docstring.split('\n')
        calculate_indent = sys.maxsize
        for line in lines[1:]:
            stripped = line.lstrip()
            if len(stripped) > 0:
                calculate_indent = min(
                    calculate_indent,
                    len(line) - len(stripped)
                )
        calculate_indent = min(
            calculate_indent,
            len(lines[-1]) - len(lines[-1].lstrip())
        )
        # Remove indentation (first line is special):
        trimmed = [lines[0]]
        if calculate_indent < sys.maxsize:
            trimmed += [line[calculate_indent:] for line in lines[1:]]

        self.write(quote)
        if len(trimmed) == 0:
            self.print_(quote)
        elif len(trimmed) == 1:
            self.print_(trimmed[0], quote)
        else:
            self.print_(trimmed[0])
            for line in trimmed[1:-1]:
                self.print_(indent, line)
            self.print_(indent, trimmed[-1], quote)

    def n_return_stmt(self, node):
        if self._params['isLambda']:
            self.preorder(node[0])
            self.prune()
        else:
            self.write(self.indent, 'return')
            RETURN = AST(
                'return_stmt',
                [
                    AST('ret_expr', [NONE]),
                    Token('RETURN_VALUE')
                ]
            )
            if self.return_none or node != RETURN:
                self.write(' ')
                self.preorder(node[0])
            self.print_()
            self.prune()  # stop recursing

    def n_return_if_stmt(self, node):
        if self._params['isLambda']:
            self.preorder(node[0])
            self.prune()
        else:
            self.write(self.indent, 'return')
            RETURN_IF = AST(
                'return_stmt',
                [
                    AST('ret_expr', [NONE]),
                    Token('RETURN_END_IF')
                ]
            )
            if self.return_none or node != RETURN_IF:
                self.write(' ')
                self.preorder(node[0])
            self.print_()
            self.prune()

    def n_yield(self, node):
        self.write('yield')
        if node != AST('yield', [NONE, Token('YIELD_VALUE')]):
            self.write(' ')
            self.preorder(node[0])
        self.prune()

    def n_buildslice3(self, node):
        p = self.prec
        self.prec = 100
        if node[0] != NONE:
            self.preorder(node[0])
        self.write(':')
        if node[1] != NONE:
            self.preorder(node[1])
        self.write(':')
        if node[2] != NONE:
            self.preorder(node[2])
        self.prec = p
        self.prune()

    def n_buildslice2(self, node):
        p = self.prec
        self.prec = 100
        if node[0] != NONE:
            self.preorder(node[0])
        self.write(':')
        if node[1] != NONE:
            self.preorder(node[1])
        self.prec = p
        self.prune()

#    def n_l_stmts(self, node):
#        if node[0] == '_stmts':
#            if len(node[0]) >= 2 and node[0][1] == 'stmt':
#                if node[0][-1][0] == 'continue_stmt':
#                    del node[0][-1]
#        self.default(node)

    def n_expr(self, node):
        p = self.prec
        if node[0].type.startswith('binary_expr'):
            n = node[0][-1][0]
        else:
            n = node[0]
        self.prec = PRECEDENCE.get(n, -2)
        if n == 'LOAD_CONST' and repr(n.argval)[0] == '-':
            self.prec = 6
        if p < self.prec:
            self.write('(')
            self.preorder(node[0])
            self.write(')')
        else:
            self.preorder(node[0])
        self.prec = p
        self.prune()

    def n_ret_expr(self, node):
        if len(node) == 1 and node[0] == 'expr':
            self.n_expr(node[0])
        else:
            self.n_expr(node)

    n_ret_expr_or_cond = n_expr

    def n_binary_expr(self, node):
        self.preorder(node[0])
        self.write(' ')
        self.preorder(node[-1])
        self.write(' ')
        self.prec -= 1
        self.preorder(node[1])
        self.prec += 1
        self.prune()

    def n_LOAD_CONST(self, node):
        data = node.argval
        datatype = type(data)
        if datatype is IntType and data == minint:
            # convert to hex, since decimal representation
            # would result in 'LOAD_CONST; UNARY_NEGATIVE'
            # change:hG/2002-02-07: this was done for all negative integers
            # todo: check whether this is necessary in Python 2.1
            self.write(hex(data))
        elif datatype is EllipsisType:
            self.write('...')
        elif data is None:
            # LOAD_CONST 'None' only occurs, when None is
            # implicit eg. in 'return' w/o params
            # pass
            self.write('None')
        else:
            self.write(repr(data))
        # LOAD_CONST is a terminal, so stop processing/recursing early
        self.prune()

    def n_delete_subscr(self, node):
        which = node[-2][0]
        if which == 'build_list' and which[-1].type.startswith('BUILD_TUPLE'):
            if which[-1] != 'BUILD_TUPLE_0':
                which.type = 'build_tuple2'
        self.default(node)

    n_store_subscr = n_binary_subscr = n_delete_subscr

    def n_tryfinallystmt(self, node):
        which = node[1][0]
        if len(which) == 1 and which[0] == 'stmt':
            if which[0][0] == 'trystmt':
                which[0][0].type = 'tf_trystmt'
            if which[0][0] == 'tryelsestmt':
                which[0][0].type = 'tf_tryelsestmt'
        self.default(node)

    def n_exec_stmt(self, node):
        """
        exec_stmt ::= expr exprlist DUP_TOP EXEC_STMT
        exec_stmt ::= expr exprlist EXEC_STMT
        """
        self.write(self.indent, 'exec ')
        self.preorder(node[0])
        if node[1][0] != NONE:
            sep = ' in '
            for subnode in node[1]:
                self.write(sep)
                sep = ", "
                self.preorder(subnode)
        self.print_()
        self.prune()

    def n_ifelsestmt(self, node, preprocess=0):
        n = node[3][0]
        if len(n) == 1 == len(n[0]) and n[0] == '_stmts':
            n = n[0][0][0]
        elif n[0].type in ('lastc_stmt', 'lastl_stmt'):
            n = n[0][0]
        else:
            if not preprocess:
                self.default(node)
            return

        if n.type in ('ifstmt', 'iflaststmt', 'iflaststmtl'):
            node.type = 'ifelifstmt'
            n.type = 'elifstmt'
        elif n.type in ('ifelsestmtr',):
            node.type = 'ifelifstmt'
            n.type = 'elifelsestmtr'
        elif n.type in ('ifelsestmt', 'ifelsestmtc', 'ifelsestmtl'):
            node.type = 'ifelifstmt'
            self.n_ifelsestmt(n, preprocess=1)
            if n == 'ifelifstmt':
                n.type = 'elifelifstmt'
            elif n.type in ('ifelsestmt', 'ifelsestmtc', 'ifelsestmtl'):
                n.type = 'elifelsestmt'
        if not preprocess:
            self.default(node)

    n_ifelsestmtc = n_ifelsestmtl = n_ifelsestmt

    def n_ifelsestmtr(self, node):
        if len(node[2]) != 2:
            self.default(node)
        which = node[2][0]
        if not isifsentence(which[0][0]) and not isifsentence(which[-1][0]):
            self.default(node)
            return

        self.write(self.indent, 'if ')
        self.preorder(node[0])
        self.print_(':')
        self.indentMore()
        self.preorder(node[1])
        self.indentLess()

        if_ret_at_end = False
        which = node[2][0]
        if len(which) >= 3:
            if isifsentence(which[-1][0]):
                if_ret_at_end = True

        past_else = False
        prev_stmt_is_if_ret = True
        for n in node[2][0]:
            if isifsentence(n[0]):
                if prev_stmt_is_if_ret:
                    n[0].type = 'elifstmt'
                prev_stmt_is_if_ret = True
            else:
                prev_stmt_is_if_ret = False
                if not past_else and not if_ret_at_end:
                    self.print_(self.indent, 'else:')
                    self.indentMore()
                    past_else = True
            self.preorder(n)
        if not past_else or if_ret_at_end:
            self.print_(self.indent, 'else:')
            self.indentMore()
        self.preorder(node[2][1])
        self.indentLess()
        self.prune()

    def n_elifelsestmtr(self, node):
        if len(node[2]) != 2:
            self.default(node)
        for n in node[2][0]:
            if not isifsentence(n[0]):
                self.default(node)
                return
        self.write(self.indent, 'elif ')
        self.preorder(node[0])
        self.print_(':')
        self.indentMore()
        self.preorder(node[1])
        self.indentLess()
        for n in node[2][0]:
            n[0].type = 'elifstmt'
            self.preorder(n)
        self.print_(self.indent, 'else:')
        self.indentMore()
        self.preorder(node[2][1])
        self.indentLess()
        self.prune()

    def n_import_as(self, node):
        iname = node[0].argval
        assert node[-1][-1].type.startswith('STORE_')
        sname = node[-1][-1].argval  # assume one of STORE_.... here
        if iname == sname or iname.startswith(sname + '.'):
            self.write(iname)
        else:
            self.write(iname, ' as ', sname)
        self.prune()

    n_import_as_cont = n_import_as

    def n_importfrom(self, node):
        if node[0].argval > 0:
            node[2].argval = '.' * node[0].argval + node[2].argval
        self.default(node)

    n_importstar = n_importfrom

    def n_mkfunc(self, node):
        self.write(node[-2].attr.co_name)  # = code.co_name
        self.indentMore()
        self.make_function(node, isLambda=0)
        if len(self._param_stack) > 1:
            self.write('\n\n')
        else:
            self.write('\n\n\n')
        self.indentLess()
        self.prune()  # stop recursing

    def n_mklambda(self, node):
        self.make_function(node, isLambda=1)
        self.prune()

    def n_list_compr(self, node):
        p = self.prec
        self.prec = 27
        n = node[-1]
        assert n == 'list_iter'
        # find innerst node
        while n == 'list_iter':
            n = n[0]  # recurse one step
            if n == 'list_for':
                n = n[3]
            elif n == 'list_if':
                n = n[2]
            elif n == 'list_if_not':
                n = n[2]
        assert n == 'lc_body'
        self.write('[')
        self.preorder(n[0])  # lc_body
        self.preorder(node[-1])  # for/if parts
        self.write(']')
        self.prec = p
        self.prune()

    def comprehension_walk(self, node, iter_index):
        p = self.prec
        self.prec = 27
        code = node[-5].argval

        assert type(code) == CodeType
        code = Code(code, self.scanner, self.currentclass)
        ast = self.build_ast(code._tokens, code._customize)
        self.customize(code._customize)
        ast = ast[0][0][0]

        n = ast[iter_index]
        assert n == 'comp_iter'
        # find innerst node
        while n == 'comp_iter':
            n = n[0]  # recurse one step
            if n == 'comp_for':
                n = n[3]
            elif n == 'comp_if':
                n = n[2]
            elif n == 'comp_ifnot':
                n = n[2]
        assert n == 'comp_body', ast

        self.preorder(n[0])
        self.write(' for ')
        self.preorder(ast[iter_index-1])
        self.write(' in ')
        self.preorder(node[-3])
        self.preorder(ast[iter_index])
        self.prec = p

    def n_genexpr(self, node):
        self.write('(')
        self.comprehension_walk(node, 3)
        self.write(')')
        self.prune()

    def n_setcomp(self, node):
        self.write('{')
        self.comprehension_walk(node, 4)
        self.write('}')
        self.prune()

    n_dictcomp = n_setcomp

    def n_classdef(self, node):
        # class definition ('class X(A,B,C):')
        cclass = self.currentclass
        self.currentclass = str(node[0].argval)

        self.write('\n\n')
        self.write(self.indent, 'class ', self.currentclass)
        self.print_super_classes(node)
        self.print_(':')

        # class body
        self.indentMore()
        self.build_class(node[2][-2].attr)
        self.indentLess()

        self.currentclass = cclass
        if len(self._param_stack) > 1:
            self.write('\n\n')
        else:
            self.write('\n\n\n')

        self.prune()

    n_classdefdeco2 = n_classdef

    def print_super_classes(self, node):
        node = node[1][0]
        if not (node == 'build_list'):
            return

        self.write('(')
        line_separator = ', '
        sep = ''
        for elem in node[:-1]:
            value = self.traverse(elem)
            self.write(sep, value)
            sep = line_separator

        self.write(')')

    def n_mapexpr(self, node):
        """
        prettyprint a mapexpr
        'mapexpr' is something like k = {'a': 1, 'b': 42 }"
        """
        p = self.prec
        self.prec = 100
        assert node[-1] == 'kvlist'
        node = node[-1]  # goto kvlist

        self.indentMore(INDENT_PER_LEVEL)
        line_seperator = ',\n' + self.indent
        sep = INDENT_PER_LEVEL[:-1]
        self.write('{')
        for kv in node:
            assert kv in ('kv', 'kv2', 'kv3')
            # kv ::= DUP_TOP expr ROT_TWO expr STORE_SUBSCR
            # kv2 ::= DUP_TOP expr expr ROT_THREE STORE_SUBSCR
            # kv3 ::= expr expr STORE_MAP
            if kv == 'kv':
                name = self.traverse(kv[-2], indent='')
                value = self.traverse(
                    kv[1],
                    indent=self.indent+(len(name)+2)*' '
                )
            elif kv == 'kv2':
                name = self.traverse(kv[1], indent='')
                value = self.traverse(
                    kv[-3],
                    indent=self.indent+(len(name)+2)*' '
                )
            elif kv == 'kv3':
                name = self.traverse(kv[-2], indent='')
                value = self.traverse(
                    kv[0],
                    indent=self.indent+(len(name)+2)*' '
                )
            self.write(sep, name, ': ', value)
            sep = line_seperator
        self.write('}')
        self.indentLess(INDENT_PER_LEVEL)
        self.prec = p
        self.prune()

    def n_build_list(self, node):
        """
        prettyprint a list or tuple
        """
        p = self.prec
        self.prec = 100
        lastnode = node.pop().type
        if lastnode.startswith('BUILD_LIST'):
            self.write('[')
            endchar = ']'
        elif lastnode.startswith('BUILD_TUPLE'):
            self.write('(')
            endchar = ')'
        elif lastnode.startswith('BUILD_SET'):
            self.write('{')
            endchar = '}'
        elif lastnode.startswith('ROT_TWO'):
            self.write('(')
            endchar = ')'
        else:
            raise 'Internal Error: n_build_list expects list or tuple'

        self.indentMore(INDENT_PER_LEVEL)
        if len(node) > 3:
            line_separator = ',\n' + self.indent
        else:
            line_separator = ', '
        sep = INDENT_PER_LEVEL[:-1]
        for elem in node:
            if (elem == 'ROT_THREE'):
                continue

            assert elem == 'expr'
            value = self.traverse(elem)
            self.write(sep, value)
            sep = line_separator
        if len(node) == 1 and lastnode.startswith('BUILD_TUPLE'):
            self.write(',')
        self.write(endchar)
        self.indentLess(INDENT_PER_LEVEL)
        self.prec = p
        self.prune()

    def n_unpack(self, node):
        for n in node[1:]:
            if n[0].type == 'unpack':
                n[0].type = 'unpack_w_parens'
        self.default(node)

    n_unpack_w_parens = n_unpack

    def n_assign2(self, node):
        for n in node[-2:]:
            if n[0] == 'unpack':
                n[0].type = 'unpack_w_parens'
        self.default(node)

    def n_assign3(self, node):
        for n in node[-3:]:
            if n[0] == 'unpack':
                n[0].type = 'unpack_w_parens'
        self.default(node)

    def n_except_cond2(self, node):
        if node[5][0] == 'unpack':
            node[5][0].type = 'unpack_w_parens'
        self.default(node)

    def engine(self, entry, startnode):
        fmt = entry[0]
        arg = 1
        i = 0
        lastC = 0
        m = escape.search(fmt)
        while m:
            i = m.end()
            self.write(m.group('prefix'))
            typ = m.group('type') or '{'
            node = startnode
            try:
                if m.group('child'):
                    node = node[int(m.group('child'))]
            except:
                print(node.__dict__)
                raise
            if typ == '%':
                self.write('%')
            elif typ == '+':
                self.indentMore()
            elif typ == '-':
                self.indentLess()
            elif typ == '|':
                self.write(self.indent)
            elif typ == ',':
                if lastC == 1:
                    self.write(',')
            elif typ == 'c':
                self.preorder(node[entry[arg]])
                arg += 1
            elif typ == 'p':
                p = self.prec
                (index, self.prec) = entry[arg]
                self.preorder(node[index])
                self.prec = p
                arg += 1
            elif typ == 'C':
                low, high, sep = entry[arg]
                lastC = remaining = len(node[low:high])
                for subnode in node[low:high]:
                    self.preorder(subnode)
                    remaining -= 1
                    if remaining > 0:
                        self.write(sep)
                arg += 1
            elif typ == 'P':
                p = self.prec
                low, high, sep, self.prec = entry[arg]
                lastC = remaining = len(node[low:high])
                for subnode in node[low:high]:
                    self.preorder(subnode)
                    remaining -= 1
                    if remaining > 0:
                        self.write(sep)
                self.prec = p
                arg += 1
            elif typ == '{':
                d = node.__dict__
                expr = m.group('expr')
                try:
                    self.write(eval(expr, d, d))
                except:
                    print(node)
                    raise
            m = escape.search(fmt, i)
        self.write(fmt[i:])

    def default(self, node):
        mapping = MAP.get(node, MAP_DIRECT)
        table = mapping[0]
        key = node
        for i in mapping[1:]:
            key = key[i]   # key = node[x1][x2]...[xN]
        if key in table:
            self.engine(table[key], node)
            self.prune()

    def customize(self, customize):
        """
        Special handling for opcodes that take a variable number
        of arguments -- we add a new entry for each in TABLE_R.
        """
        for k, v in list(customize.items()):
            if k in TABLE_R:
                continue
            op = k[:k.rfind('_')]
            if op == 'CALL_FUNCTION':
                TABLE_R[k] = ('%c(%P)', 0, (1, -1, ', ', 100))
            elif op in ('CALL_FUNCTION_VAR',
                        'CALL_FUNCTION_VAR_KW', 'CALL_FUNCTION_KW'):
                if v == 0:
                    str = '%c(%C'  # '%C' is a dummy here ...
                    p2 = (0, 0, None)  # .. because of this
                else:
                    str = '%c(%C, '
                    p2 = (1, -2, ', ')
                if op == 'CALL_FUNCTION_VAR':
                    str += '*%c)'
                    entry = (str, 0, p2, -2)
                elif op == 'CALL_FUNCTION_KW':
                    str += '**%c)'
                    entry = (str, 0, p2, -2)
                else:
                    str += '*%c, **%c)'
                    if p2[2]:
                        p2 = (1, -3, ', ')
                    entry = (str, 0, p2, -3, -2)
                TABLE_R[k] = entry

    def get_tuple_parameter(self, ast, name):
        """
        If the name of the formal parameter starts with dot,
        it's a tuple parameter, like this:
        #          def MyFunc(xx, (a,b,c), yy):
        #                  print a, b*2, c*42
        In byte-code, the whole tuple is assigned to parameter '.1' and
        then the tuple gets unpacked to 'a', 'b' and 'c'.

        Since identifiers starting with a dot are illegal in Python,
        we can search for the byte-code equivalent to '(a,b,c) = .1'
        """
        assert ast == 'stmts'
        for i in range(len(ast)):
            # search for an assign-statement
            assert ast[i][0] == 'stmt'
            node = ast[i][0][0]
            if node == 'assign' \
               and node[0] == ASSIGN_TUPLE_PARAM(name):
                # okay, this assigns '.n' to something
                del ast[i]
                # walk lhs; this
                # returns a tuple of identifiers as used
                # within the function definition
                assert node[1] == 'designator'
                # if lhs is not a UNPACK_TUPLE (or equiv.),
                # add parenteses to make this a tuple
                return '(' + self.traverse(node[1]) + ')'
        raise "Can't find tuple parameter" % name

    def make_function(self, node, isLambda, nested=1):
        """Dump function definition, doc string, and function body."""

        def build_param(ast, name, default):
            """build parameters:
                - handle defaults
                - handle format tuple parameters
            """
            # if formal parameter is a tuple, the paramater name
            # starts with a dot (eg. '.1', '.2')
            if name.startswith('.'):
                # replace the name with the tuple-string
                name = self.get_tuple_parameter(ast, name)
            if default:
                result = '%s=%s' % (name, self.traverse(default, indent=''))
                if result[-2:] == '=':  # default was 'LOAD_CONST None'
                    result += 'None'
                return result
            else:
                return name
        defparams = node[:node[-1].arg]  # node[-1] == MAKE_xxx_n
        code = node[-2].argval
        assert type(code) == CodeType
        code = Code(code, self.scanner, self.currentclass)
        # add defaults values to parameter names
        argc = code.co_argcount
        paramnames = list(code.co_varnames[:argc])
        # defaults are for last n parameters, thus reverse
        paramnames.reverse()
        defparams.reverse()
        try:
            ast = self.build_ast(code._tokens,
                                 code._customize,
                                 isLambda=isLambda,
                                 noneInNames=('None' in code.co_names))
        except ParserError as p:
            self.write(str(p))
            self.ERROR = p
            return
        # build parameters
        from itertools import izip_longest
        params = [
            build_param(ast, name, default)
            for name, default in izip_longest(paramnames, defparams)
        ]
        params.reverse()  # back to correct order
        if 4 & code.co_flags:   # flag 2 -> variable number of args
            params.append('*%s' % code.co_varnames[argc])
            argc += 1
        if 8 & code.co_flags:   # flag 3 -> keyword args
            params.append('**%s' % code.co_varnames[argc])
            argc += 1
        # dump parameter list (with default values)
        indent = self.indent
        if isLambda:
            self.write("lambda ", ", ".join(params), ": ")
        else:
            self.print_("(", ", ".join(params), "):")
        if len(code.co_consts) and code.co_consts[0] is not None:
            # docstring exists, dump it
            self.print_docstring(indent, code.co_consts[0])
        code._tokens = None  # save memory
        # assert ast == 'stmts'
        all_globals = find_all_globals(ast, set())
        for g in ((all_globals & self.mod_globs) | find_globals(ast, set())):
            self.print_(self.indent, 'global ', g)
        self.mod_globs -= all_globals
        rn = ('None' in code.co_names) and not find_none(ast)
        self.gen_source(ast, code._customize, isLambda=isLambda, returnNone=rn)
        code._tokens = None
        code._customize = None  # save memory

    def build_class(self, code):
        """Dump class definition, doc string and class body."""
        assert type(code) == CodeType
        code = Code(code, self.scanner, self.currentclass)
        indent = self.indent
        ast = self.build_ast(code._tokens, code._customize)
        code._tokens = None  # save memory
        assert ast == 'stmts'
        if ast[0][0] == NAME_MODULE:
            del ast[0]
        # if docstring exists, dump it
        if code.co_consts and code.co_consts[0] is not None and ast[0][0] == ASSIGN_DOC_STRING(code.co_consts[0]):
            self.print_docstring(indent, code.co_consts[0])
            self.print_()
            del ast[0]
        # the function defining a class normally returns locals(); we
        # don't want this to show up in the source, thus remove the node
        if ast[-1][0] == RETURN_LOCALS:
            del ast[-1]  # remove last node
        for g in find_globals(ast, set()):
            self.print_(indent, 'global ', g)
        self.gen_source(ast, code._customize)
        code._tokens = None
        code._customize = None  # save memory

    def gen_source(self, ast, customize, isLambda=0, returnNone=False):
        """convert AST to source code"""
        rn = self.return_none
        self.return_none = returnNone
        # if code would be empty, append 'pass'
        if len(ast) == 0:
            self.print_(self.indent, 'pass')
        else:
            self.customize(customize)
            if isLambda:
                self.write(self.traverse(ast, isLambda=isLambda))
            else:
                self.print_(self.traverse(ast, isLambda=isLambda))
        self.return_none = rn

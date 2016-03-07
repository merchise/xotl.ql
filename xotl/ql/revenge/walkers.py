# -*- encoding: utf-8 -*-
# ---------------------------------------------------------------------
# xotl.ql.revenge.walkers
# ---------------------------------------------------------------------
# Copyright (c) 2014-2016 Merchise Autrement and Contributors
# All rights reserved.
#

#  Copyright (c) 1999 John Aycock
#  Copyright (c) 2000-2002 by hartmut Goebel <h.goebel@crazy-compilers.com>
#  Copyright (c) 2005 by Dan Pascu <dan@windowmaker.org>
#
#  See main module for license.
#

#  flake8: noqa

from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)

import sys
try:
    from types import EllipsisType, IntType
except ImportError:
    EllipsisType = type(Ellipsis)
    IntType = int

from .spark import GenericASTTraversal
from . import parsers, qst
from .parsers import AST
from .scanners import Token

from .tools import pushto, take, pop_until_sentinel
from .tools import CODE_HAS_KWARG, CODE_HAS_VARARG

from .eight import py3k as _py3, _py_version


minint = -sys.maxsize-1

# Helper: decorators that push/take item to/from a stack.
take_n = lambda n: take(n, '_stack', 'children')
take_one = take_n(1)
take_two = take_n(2)
take_three = take_n(3)


def pushtostack(f):
    @pushto('_stack')
    def inner(self, *args, **kw):
        return f(self, *args, **kw)
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
            uncompyled = Uncompyled(code,
                                    islambda=islambda,
                                    hasnone=hasnone)
            # XXX: uncompyled.qst will contain a qst.Expression, but we need
            # to keep only the body.
            self._stack.append(uncompyled.qst.body)
            # Argument names are the first of co_varnames
            argcount = code.co_argcount
            varnames = code.co_varnames
            args = [
                qst.Name(name, qst.Param())
                for name in varnames[:argcount]
            ]
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
            return cls(value)

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
            defaults.append(items.pop())
        kwonly = []
        kwdefaults = []
        for i in range(nkwonly):
            kw = items.pop()   # we get a qst.keyword
            kwonly.append(qst.arg(kw.arg, None))
            kwdefaults.append(kw.value)
        body = items.pop()
        args = [a for a in items.pop()]
        vararg = items.pop()
        kwarg = items.pop()
        if _py3:
            # Recast args (they were qst.Name) as qst.arg in Python 3
            args = [qst.arg(arg.id, None) for arg in args]
            if _py_version < (3, 4):
                # Before Python 3,4 the vararg and kwarg were not enclosed
                # inside qst.arg and their annotations followed them in the
                # constructor.
                arguments = qst.arguments(args, vararg, None, kwonly, kwarg,
                                          None, defaults, kwdefaults)
            else:
                vararg = qst.arg(vararg, None) if vararg else None
                kwarg = qst.arg(kwarg, None) if kwarg else None
                arguments = qst.arguments(args, vararg, kwonly, kwdefaults,
                                          kwarg, defaults)
        else:
            arguments = qst.arguments(args, vararg, kwarg, defaults)
        return qst.Lambda(arguments, body)

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
        if isinstance(right, qst.pyast.BoolOp) \
           and isinstance(right.op, qst.pyast.And):
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
        if isinstance(right, qst.pyast.BoolOp) \
           and isinstance(right.op, qst.pyast.Or):
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

    def _n_comp_exit(sentinel):
        def n_comp_exit(self, node, children=None, items=None):
            # The `item` will be ``[iterable, ...., qstComp]``, the space in
            # between is the 'inner function' arg, vararg, etc...  We can
            # safely ignore all function related args, since we're not going
            # to produce a function definition.
            #
            # But the qstComp will have its first comprehesion with the wrong
            # iterable, replace it.
            iterable = items.pop(0)
            compr = items.pop()
            compr.generators[0].iter = iterable
            return compr
        return pushtostack(take_until_sentinel(n_comp_exit, sentinel))

    n_genexpr_exit = _n_comp_exit('genexpr')

    n__py_load_setcomp = _n_walk_innerfunc(islambda=False)

    @pushsentinel
    def n_setcomp(self, node):
        pass

    n_setcomp_exit = _n_comp_exit('setcomp')

    n__py_load_dictcomp = _n_walk_innerfunc(islambda=False)

    @pushsentinel
    def n_dictcomp(self, node):
        pass

    n_dictcomp_exit = _n_comp_exit('dictcomp')

    # The comprehension stuff.
    #
    # Since `comp_if` may deeply nested and intertwined with comp_ifnot,
    # comp_for, but with a single comp_body at the very end, we simply need to
    # collect all the expressions inside the `comp_iter` and push the new if
    # expression to the stack.  But this is the default, the milestones are
    # comp_for and the top-level comprehension.  The `comp_ifnot` needs
    # rewriting cause the 'expr' needs to be negated.
    #

    def _n_compfunc_exit(qstClass, sentinel):
        def n_compfunc_exit(self, node, children=None, items=None):
            # At this point we should at least three items in the stack.
            # `items` will be: [elt, ...., target, iterable].
            #
            # The items in between may be partially constructed
            # `qst.comprehension` (the result of comp_for)
            elt = items.pop(0)
            iterable = items.pop()
            assert getattr(iterable, 'id', '').startswith('.')
            target = items.pop()
            ifs = []
            while items and not isinstance(items[-1], qst.pyast.comprehension):
                item = items.pop()
                ifs.append(item)
            comprehensions = list(reversed(items)) if items else []
            comprehensions.insert(0, qst.comprehension(target, iterable, ifs))
            # XXX: Wrap it in an Expression since it will be unwrapped by
            # _walk_innerfunc
            return qst.Expression(qstClass(elt, comprehensions))
        return pushtostack(take_until_sentinel(n_compfunc_exit, sentinel))

    @pushsentinel
    def n_genexpr_func(self, node):
        pass

    n_genexpr_func_exit = _n_compfunc_exit(qst.GeneratorExp, 'genexpr_func')

    @pushsentinel
    def n_setcomp_func(self, node):
        pass

    n_setcomp_func_exit = _n_compfunc_exit(qst.SetComp, 'setcomp_func')

    @pushsentinel
    def n_dictcomp_func(self, node):
        pass

    def _build_DictComp(elt, generators):
        assert isinstance(elt, dict)
        key = elt['key']
        val = elt['val']
        return qst.DictComp(key, val, generators)

    n_dictcomp_func_exit = _n_compfunc_exit(
        _build_DictComp, 'dictcomp_func'
    )
    del _build_DictComp

    @pushsentinel
    def n_comp_for(self, node):
        pass

    @take_until_sentinel
    def n_comp_for_exit(self, node, children=None, items=None):
        # At this point the items should be [elt, .... , designator, iterable]
        # just like at the top level generator... the items in between are
        # conditions or other comprehensions we should leave.
        iterable = items.pop()
        target = items.pop()
        ifs = []
        # items should have more than one item to have any ifs or
        # inner generators.
        while len(items) > 1 and not isinstance(items[-1],
                                                qst.pyast.comprehension):
            ifs.append(items.pop())
        self._stack.append(qst.comprehension(target, iterable, ifs))
        for which in reversed(items):
            self._stack.append(which)

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
        return elt

    @pushtostack
    @take_two
    def n_dict_comp_body_exit(self, node, children=None):
        # Dict comprehensions always have two elt expressions: one for the
        # keys and other for the values.  This method simply wraps them in a
        # single value because the upper-production `comp_body` takes a single
        # item from the stack.  This way, both values will reach the
        # `n_dictcomp_func_exit` method, but packed, but is is easy to unpack
        # them.
        key, val = children
        return {'key': key, 'val': val}

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

    @pushsentinel
    def n_comp_ifnotor(self, node):
        pass

    @take_until_sentinel
    def n_comp_ifnotor_exit(self, node, children=None, items=None):
        # This a hack for Pypy.
        #
        #  comp_ifnotor ::= expr jmp_false expr jmp_true JUMP_BACK comp_iter
        #
        #  It wraps the pattern if not ... or ... in a comprehension.
        #
        false = items.pop()
        true = items.pop()
        self._stack.append(
            qst.BoolOp(
                qst.Or(),
                [qst.UnaryOp(qst.Not(), false), true]
            )
        )
        for item in reversed(items):
            self._stack.append(item)

    @pushsentinel
    def n_comp_ifornot(self, node):
        pass

    @take_until_sentinel
    def n_comp_ifornot_exit(self, node, children=None, items=None):
        # This a hack for Pypy.
        #
        #  comp_ifornot ::= expr jmp_true expr jmp_false JUMP_BACK comp_iter
        #
        #  It wraps the pattern if not ... or ... in a comprehension.
        #
        true = items.pop()
        false = items.pop()
        self._stack.append(
            qst.BoolOp(
                qst.Or(),
                [
                    true,
                    qst.UnaryOp(
                        qst.Not(), false
                    ),
                ]
            )
        )
        for item in reversed(items):
            self._stack.append(item)

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

    del _n_walk_innerfunc, _n_compfunc_exit, _n_comp_exit

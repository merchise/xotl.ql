#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------
# Copyright (c) Merchise Autrement [~º/~] and Contributors
# All rights reserved.
#
# This is free software; you can do what the LICENCE file allows you to.
#

from xoutil.modules import moduleproperty


def pushto(attr):
    '''Makes a method push is result to `self.<attr>`.

    '''
    from xoutil.objects import setdefaultattr

    def decorator(f):
        def inner(self, *args, **kwargs):
            res = f(self, *args, **kwargs)
            setdefaultattr(self, attr, []).append(res)
            return res
        return inner
    return decorator


def take(n, attr, kwargname):
    '''Makes a method that takes `n` items from the stack `self.<attr>` and
    passes it as keyword `kwargname`.

    Items are passed in extraction-order.  For instance, if the stack (as a
    list) contains the item ``[1, 2, 3, 4]``, and `n` is 3, the keyword
    argument will have the tuple ``(4, 3, 2)``.

    '''
    from xoutil.objects import setdefaultattr

    def decorator(f):
        def inner(self, *args, **kwargs):
            stack = setdefaultattr(self, attr, [])
            items = pop_n(stack, n)
            kwargs[kwargname] = tuple(items)
            return f(self, *args, **kwargs)
        return inner
    return decorator


def pop_n(stack, n):
    '''Pop n items from the stack.

    If there are less than `n` items in the stack, raise an IndexError.

    .. note:: Code that catches the IndexError, will see the stack empty.

    The items are returned in pop-order: if stack is ``[1, 2, 3, 4]`` and `n`
    is 2, the result would be ``[4, 3]``.

    '''
    if len(stack) < n:
        stack[:] = []  # Just in case some try/except
        raise IndexError('Popping too many items from the stack')
    items = stack[-n:]
    del stack[-n:]
    items.reverse()
    return items


def pop_until_sentinel(stack, sentinel):
    '''Pop from the stack until a 'sentinel' object is found.

    Return the list of objects pop in the order they were collected from the
    stack.

    If the sentinel is not found when the stack is exhausted, raise an
    IndexError.

    '''
    try:
        pos = lastindex(stack, sentinel)
    except ValueError:
        raise IndexError
    items = pop_n(stack, len(stack) - pos)
    items.pop()  # this is the sentinel
    return items


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
    from xoutil.string import cut_any_prefix, cut_suffix
    name = name if name else f.__name__
    name = cut_suffix(cut_any_prefix(name, 'n_', '_n_'), '_exit')
    return (name, node)


def split(iterable, predicate):
    true, false = [], []
    for item in iter(iterable):
        if predicate(item):
            true.append(item)
        else:
            false.append(item)
    return true, false


def even(n):
    return n % 2 == 0


def CODE_HAS_VARARG(code):
    return code.co_flags & 0x04


def CODE_HAS_KWARG(code):
    return code.co_flags & 0x08


def CO_GENERATOR(code):
    return code.co_flags & 0x20


def CO_NESTED(code):
    return code.co_flags & 0x0010


def CO_COROUTINE(code):
    return code.co_flags & 0x0080


def CO_ITERABLE_COROUTINE(code):
    return code.co_flags & 0x0100


@moduleproperty
def WORDS_BIGENDIAN(self):
    '''True if opcode is the high-byte of each bytecode.

    See the file Python/wordcode_helpers.h.  There the PACKOPARG is defined
    depending on how Python was configured.

    '''
    # Since lambda: None is
    #
    #   0  LOAD_CONST       None
    #   2  RETURN_VALUE
    #
    # We simply find the index of the in the code str
    import dis
    LOAD_CONST = dis.opmap['LOAD_CONST']
    return (lambda: None).__code__.co_code.index(LOAD_CONST) == 0


def PACKOPARG(opcode, oparg):
    if not WORDS_BIGENDIAN:  # XXX: WHY the `not`?
        return (opcode << 8) | oparg
    else:
        return (oparg << 8) | opcode


def lastindex(lst, which):
    '''Finds the last occurrence of `which` in the list.

    If `which` is not in the list, raise an ValueError.

    '''
    lst.reverse()
    try:
        return len(lst) - lst.index(which) - 1
    finally:
        lst.reverse()

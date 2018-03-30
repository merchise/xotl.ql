#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------
# Copyright (c) Merchise Autrement [~º/~] and Contributors
# All rights reserved.
#
# This is free software; you can do what the LICENCE file allows you to.
#


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
    items = []
    for _ in range(n):
        items.append(stack.pop())
    return items


def pop_until_sentinel(stack, sentinel):
    '''Pop from the stack until a 'sentinel' object is found.

    Return the list of objects pop in the order they were collected from the
    stack.

    If the sentinel is not found when the stack is exhausted, raise an
    IndexError.

    '''
    item, items = None, []
    while item != sentinel:
        item = stack.pop()
        if item != sentinel:
            items.append(item)
    return items


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

#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# ---------------------------------------------------------------------
# tools
# ---------------------------------------------------------------------
# Copyright (c) 2015 Merchise Autrement and Contributors
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the LICENCE attached (see LICENCE file) in the distribution
# package.
#
# Created on 2015-11-12

'''

'''

from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)


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
    '''Makes a method take `n` items from the stack `self.<attr>` and passes
    it as keyword `kwargname`.

    Items are passed in extraction-order.  For instance, if the stack (as a
    list) contains the item ``[1, 2, 3, 4]``, and `n` is 3, the keyword
    argument will have the tuple ``(4, 3, 2)``.

    '''
    from xoutil.objects import setdefaultattr

    def decorator(f):
        def inner(self, *args, **kwargs):
            stack = setdefaultattr(self, attr, [])
            items = []
            for _ in range(n):
                items.append(stack.pop())
            kwargs[kwargname] = tuple(items)
            return f(self, *args, **kwargs)
        return inner
    return decorator

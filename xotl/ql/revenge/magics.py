# TODO:  See if we need this, we probably won't be reading .pyc files, so
# it's likely this will disappear.

from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)

import struct

__all__ = ['magics', 'versions']


def __build_magic(magic):
    from xoutil.eight import _py3
    if _py3:
        return struct.pack(str('Hcc'), magic, '\r'.encode(), '\n'.encode())
    else:
        return struct.pack(str('Hcc'), magic, str('\r'), str('\n'))


def __by_version(magics):
    by_version = {}
    for m, v in list(magics.items()):
        by_version[v] = m
    return by_version


# taken from from Lib/importlib/_bootstrap.py in recent (3.5a) CPython.
versions = {

    __build_magic(62171): '2.7',  # 2.7a0 (optimize list comprehensions/change
                                  # LIST_APPEND)

    __build_magic(62181): '2.7',  # 2.7a0 (optimize conditional branches:
                                  # introduce POP_JUMP_IF_FALSE and #
                                  # POP_JUMP_IF_TRUE)

    __build_magic(62191): '2.7',  # 2.7a0 (introduce SETUP_WITH)
    __build_magic(62201): '2.7',  # 2.7a0 (introduce BUILD_SET)
    __build_magic(62211): '2.7',  # 2.7a0 (introduce MAP_ADD and SET_ADD)

    __build_magic(3000):  '3.0',  # Python 3000 --
    __build_magic(3010):  '3.0',  # -- (removed UNARY_CONVERT)
    __build_magic(3020):  '3.0',  # 3020 (added BUILD_SET)
    __build_magic(3030):  '3.0',  # 3030 (added keyword-only parameters)
    __build_magic(3040):  '3.0',  # (added signature annotations)
    __build_magic(3050):  '3.0',  # (print becomes a function)
    __build_magic(3060):  '3.0',  # (PEP 3115 metaclass syntax)
    __build_magic(3061):  '3.0',  # (string literals become unicode)
    __build_magic(3071):  '3.0',  # (PEP 3109 raise changes)

    __build_magic(3081):  '3.0',  # (PEP 3137 make __file__ and __name__
                                  # unicode)

    __build_magic(3091):  '3.0',  # (kill str8 interning)
    __build_magic(3101):  '3.0',  # (merge from 2.6a0, see 62151)
    __build_magic(3103):  '3.0',  # (__file__ points to source file)
    __build_magic(3111):  '3.0',  # 3.0a4: 3111 (WITH_CLEANUP optimization).

    __build_magic(3131):  '3.0',  # 3.0a5: 3131 (lexical exception
                                  # stacking, including POP_EXCEPT)

    __build_magic(3141):  '3.0',  # 3.1a0: 3141 (optimize list, set and
                                  # dict comprehensions: change
                                  # LIST_APPEND and SET_ADD, add MAP_ADD)

    __build_magic(3151):  '3.1',  # 3.1a0: 3151 (optimize conditional
                                  # branches: introduce POP_JUMP_IF_FALSE
                                  # and POP_JUMP_IF_TRUE)

    __build_magic(3160):  '3.2',  # 3.2a0: 3160 (add SETUP_WITH)
                                  # tag: cpython-32

    __build_magic(3170):  '3.2',  # 3.2a1: 3170 (add DUP_TOP_TWO, remove
                                  # DUP_TOPX and ROT_FOUR) tag: cpython-32

    __build_magic(3180):  '3.2',  # 3.2a2  3180 (add DELETE_DEREF)

    __build_magic(3190):  '3.3',  # 3.3a0 3190 __class__ super closure changed

    __build_magic(3200):  '3.3',  # 3.3a0  3200 (__qualname__ added)

    __build_magic(3210):  '3.3',  # (added size modulo 2**32 to the pyc
                                  # header)

    __build_magic(3220):  '3.3',  # 3.3a1 3220 (changed PEP 380
                                  # implementation)

    __build_magic(3230):  '3.3',  # 3.3a4 3230 (revert changes to implicit
                                  # __class__ closure)

    __build_magic(3250):  '3.4',  # 3.4a1 3250 (evaluate positional default
                                  # arguments before keyword-only defaults)

    __build_magic(3260):  '3.4',  # 3.4a1 3260 (add LOAD_CLASSDEREF; allow
                                  # locals of class to override free vars)

    __build_magic(3270):  '3.4',  # 3.4a1 3270 (various tweaks to the
                                  # __class__ closure)

    __build_magic(3280):  '3.4',  # 3.4a1 3280 (remove implicit class
                                  # argument)

    __build_magic(3290):  '3.4',  # 3.4a4 3290 (changes to __qualname__
                                  # computation)

    __build_magic(3300):  '3.4',  # 3.4a4 3300 (more changes to __qualname__
                                  # computation)

    __build_magic(3310):  '3.4',  # 3.4rc2 3310 (alter __qualname__
                                  # computation)

    __build_magic(3320):  '3.5',  # 3.5a0 3320 (matrix multiplication
                                  # operator)

}

magics = __by_version(versions)


def __show(text, magic):
    print(text, struct.unpack('BBBB', magic), struct.unpack('HBB', magic))


def test():
    import imp
    magic_34 = magics['3.4']
    current = imp.get_magic()
    current_version = versions[current]
    magic_current = magics[current_version]
    print('This Python interpreter has version', current_version)
    __show('imp.get_magic():\t', current),
    __show('magic[current_version]:\t', magic_current)
    __show('magic_34:\t\t', magic_34)

if __name__ == '__main__':
    test()

from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)


def inorder(t):
    if t:
        for x in inorder(t.left):
            yield x
        yield t.label
        for x in inorder(t.right):
            yield x

def generate_ints(n):
    for i in range(n):
        yield i*2

for i in generate_ints(5):
    print(i, end=' ')
print()
gen = generate_ints(3)
print(next(gen), end=' ')
print(next(gen), end=' ')
print(next(gen), end=' ')
print(next(gen))

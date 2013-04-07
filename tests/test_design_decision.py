#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#----------------------------------------------------------------------
# xotl.ql.tests.test_design_decision
#----------------------------------------------------------------------
# Copyright (c) 2012, 2013 Merchise Autrement
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under
# the terms of the LICENCE attached in the distribution package.
#
# Created on 13 déc. 2012


from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        unicode_literals as _py3_unicode,
                        absolute_import as _py3_abs_imports)

try:
    import pytest
except ImportError:
    import contextlib
    class pytest:
        class _marks:
            __getattr__ = lambda s, x: (lambda *a, **k: (lambda f: f))
        marks = mark = _marks()

        @staticmethod
        @contextlib.contextmanager
        def raises(x):
            yield

from xoutil.context import context
from xoutil.proxy import UNPROXIFING_CONTEXT, unboxed

from xotl.ql import this
from xotl.ql.core import these, QueryParticlesBubble
from xotl.ql.expressions import EXPRESSION_CONTEXT
from xotl.ql.interfaces import ITerm, IBoundTerm

__docstring_format__ = 'rst'
__author__ = 'manu'


def bubbling():
    res = context(EXPRESSION_CONTEXT)
    res.data.bubble = QueryParticlesBubble()
    return res


'''
Tests that are not functional. This suite only tests design
decisions that may change over time; but which should not affect
the result of ``these(<comprehension>)`` syntax *unless* there's
a change in Query Language API.
'''

def test_yield_once_per_query():
    q = (a for c in this for b in c.bs for a in b.a)
    assert next(q) is not None
    with pytest.raises(StopIteration):
        next(q)

    # TODO: Document how to obtain the queries
    qs = (a for i in range(3) for b in this('b' + str(i)) for a in b.a)
    for i in range(3):
        expected = this('b' + str(i)).a
        returned = next(qs)
        with context(UNPROXIFING_CONTEXT):
            assert expected == returned
    with pytest.raises(StopIteration):
        next(qs)


def test_plain_iter():
    with bubbling():
        t1 = next(iter(this))
    with context(UNPROXIFING_CONTEXT):
        assert IBoundTerm.providedBy(t1)

    t1 = next(parent for parent in this('parent'))
    assert 'parent' == unboxed(t1).name

    t1 = next(parent for parent in this('parent').children)
    assert 'children' == unboxed(t1).name


def test_basic_queries_building():
    with bubbling() as current:
        expr = next(parent.title + parent.name
                    for parent in this('parent')
                    if (parent.age > 32) & parent.married & parent.spouse.alive)
        parts = current.data.bubble.parts
    assert len(parts) == 2  # filter + selection

    # The select part is at the top
    assert "this('parent').title + this('parent').name" == str(parts[-1])
    # Then the binding
    assert ("((this('parent').age > 32) and this('parent').married) and "
            "this('parent').spouse.alive" == str(parts[-2]))
    with pytest.raises(IndexError):
        print(str(parts[-3]))


def test_complex_query_building():
    with bubbling() as current:
        parent, child = next((parent.title + parent.name,
                              child.name + child.nick)
                             for parent in this('parent')
                             if (parent.age > 32) & parent.children
                             for child in parent.children
                             if child.age < 5)
        parts = current.data.bubble.parts

    assert len(parts) == 4  # 2 filters + 2 selections

    parent = this('parent')
    child = parent.children
    assert str(child.name + child.nick) == str(parts[-1])
    assert str(parent.title + parent.name) == str(parts[-2])
    assert str(child.age < 5) == str(parts[-3])
    assert str((parent.age > 32) & parent.children) == str(parts[-4])
    with pytest.raises(IndexError):
        print(str(parts[-5]))


def test_free_terms_are_not_captured():
    from xotl.ql.expressions import any_
    with bubbling() as current:
        next(parent
             for parent in this('parent')
             if parent.name
             if any_(this.children, this.age < 6))
        parts = current.data.bubble.parts

    assert len(parts) == 2

    pname = this('parent').name
    expected = any_(this.children, this.age < 6)
    with context(UNPROXIFING_CONTEXT):
        assert pname in parts
        assert expected in parts


def test_undetected_particles():
    from xotl.ql.expressions import any_
    with bubbling() as current:
        next(parent
             for parent in this('parent')
             if any_(child for child in parent.children if child.age < 6))
        parts = current.data.bubble.parts

    # `child.age < 6` should not be leaked
    assert 1 == len(parts)


def test_right_bindings():
    with bubbling() as current:
        next((parent, child)
             for parent in this('parent')
             if parent.children.updated_since(days=1)
             for child in parent.children
             if child.age < 4)
        # The query has two filters:
        #
        #    this('parent').children & (count(this('parent').children) > 4)
        #    this('parent').children.age < 5
        #
        # If we regard every term `this('parent').children` as the *token*,
        # what would be the meaning of the first condition? How do we
        # distinguish from conditions over the named-token and the expression
        # that generates the token?  i.e in `for child in parent.children`, the
        # `child` token is *not* the same as the term `parent.children`.
        #
        # Now the token of the relevant query might help, but then the machine
        # should not strip those tokens from query-parts.
        parts = current.data.bubble.parts
        bubble_tokens = current.data.bubble.tokens
    assert len(parts) == 2

    with context(UNPROXIFING_CONTEXT):
        parent_token = next((token
                             for token in bubble_tokens
                             if token.expression == this('parent')),
                            None)
        children_token = next((token
                               for token in bubble_tokens
                               if token.expression != this('parent')),
                              None)
    child_age_filter = parts.pop(-1)
    parent_children_updated_filter = parts.pop(-1)
    with pytest.raises(IndexError):
        parts.pop(-1)
    with context(UNPROXIFING_CONTEXT):
        child_age_term = child_age_filter.children[0]
        assert child_age_term.binding == children_token

        # Note that: parent.children.updated_since(days=1)
        # is equivalent to invoke(parent.children.updated_since, days=1)
        parent_children_term = parent_children_updated_filter.children[0]
        assert parent_children_term.binding == parent_token
        assert dict(days=1) == parent_children_updated_filter.named_children


def test_complex_query_building_with_dict():
    from xotl.ql.expressions import min_, max_
    with bubbling() as current:
        d = {parent.age: (min_(child.age), max_(child.age))
             for parent in this('parent')
             if (parent.age > 32) & parent.children
             for child in parent.children
             if child.age < 5}
        parts = current.data.bubble.parts
    assert len(parts) == 5

    def ok(which):
        assert str(which) == str(parts.pop(-1))

    parent = this('parent')
    child = parent.children
    ok(parent.age)  # The key of the dict is the top-most expression
    ok(max_(child.age))
    ok(min_(child.age))
    ok(child.age < 5)
    ok((parent.age > 32) & parent.children)
    with pytest.raises(IndexError):
        ok(None)


#        def test_query_reutilization_design():
#            from xotl.ql.expressions import is_a
#            Person = "Person"
#            persons = these(parent
#                            for parent in this('parent')
#                            if is_a(parent, Person))
#
#            these(parent for parent in persons
#                         if (parent.age < 35) & parent.children)
#
#        def test_iters_produce_a_single_name():
#            a1, a2 = next((p, p) for p in this)
#            p1, p2 = next((p, t) for p in this for t in this)
#            with context(UNPROXIFING_CONTEXT):
#                self.assertEqual(a1, a2)
#                self.assertNotEqual(p1, p2)


def test_20121022_complex_intermingled_query():
    '''Tests that toy.type == 'laptop' does not get singled out of its
    containing expression.

    The following procedure is not current any more; but we leave it
    there for historical reasons. Since the introduction of "particle
    bubble" that captures all the parts and tokens, we have removed
    the :attr:`xotl.ql.interfaces.IQueryPart.tokens`.

       Slight variation over the same test of previous testcase but
       that shows how `|` that if we don't have the `tokens` params
       things will go wrong:

       - `parent.age > 32` will have `this('parent')` as its token

       - `child.age < 5` will have `this('parent').children` as its
         token.

       - When building `(parent.age > 32) & (child.age < 5)` the
         resultant part will have only `this('parent')` as the token,
         and

       - `contains(child.toys, 'laptop')` will be attached to
         `this('parent').children`, but this will create a stack in the
         token for `child`, the stack will contain: ``child.age < 5``,
         and ``contains(child.toys, 'laptop')``, for they don't merge.

       - Then, building ``... | contains(child.toys, 'laptop')`` will
         be attached to `this('parent')` only! This will cause that the
         token `this('parent').children` will be left with a stack of
         two items that will be considered separate filters, which is
         wrong!

       The solutions seems to be simply to make
       `this('parent').children` aware of parts that are generated. So
       :attr:`xotl.ql.core.QuerPart.tokens` is born.

    '''
    with bubbling() as current:
        parent, child, toy = next(
            (parent.title + parent.name, child.name + child.nick, toy.name)

            for parent in this('parent')
            for child in parent.children
            for toy in child.toys
            if (parent.age > 32) & (child.age < 5) | (toy.type == 'laptop'))

        parts = current.data.bubble.parts
    assert len(parts) == 4  # ie. 3 selections and 1 filter


    parent = this('parent')
    child = parent.children
    def ok(x):
        assert str(x) == str(parts.pop(-1))
    toy = child.toys
    ok(toy.name)
    ok(child.name + child.nick)
    ok(parent.title + parent.name)
    ok((parent.age > 32) & (child.age < 5) | (toy.type == 'laptop'))
    with pytest.raises(IndexError):
        print(ok(None))


'''
Non-selected tokens should not be forgotten.

This tests copycats most of the test_thesey_doesnot_messup_identities
There's was two related bugs there:
   - There should be a token for rel
   - There should be a filter `is_instance(rel, Partnetship)`

'''

def test_is_a_partnership_is_not_forgotten():
    from xoutil.compat import izip
    with bubbling() as current:
        next((person, partner)
             for person, partner in izip(this('person'),
                                         this('partner'))
             for rel in this('relation')
             if rel.type == 'partnership'
             if (rel.subject == person) & (rel.object == partner))

        parts = current.data.bubble.parts
        tokens = current.data.bubble.tokens
    assert len(parts) ==  2  # Only the 2 filters

    tokens = [tk.expression for tk in tokens]
    def ok(x):
        assert str(x) == str(parts.pop(-1))
    person = this('person')
    partner = this('partner')
    rel = this('relation')
    assert person in tokens
    assert partner in tokens
    assert rel in tokens
    ok((rel.subject == person) & (rel.object == partner))
    ok(rel.type == 'partnership')
    with pytest.raises(IndexError):
        ok(None)

def test_worst_case_must_have_3_filters_and_3_tokens():
    from xoutil.compat import izip
    with bubbling() as current:
        next(person
             for person, partner in izip(this('person'),
                                         this('partner'))
             for rel in this('relation')
             if rel.type == 'partnership'
             if rel.subject == person
             if rel.object == partner
             if partner.age > 32)

        parts = current.data.bubble.parts
        tokens = current.data.bubble.tokens
    assert len(parts) == 4

    tokens = [tk.expression for tk in tokens]
    def ok(x):
        assert str(x) == str(parts.pop(-1))
    person = this('person')
    partner = this('partner')
    rel = this('relation')
    assert person in tokens
    assert partner in tokens
    assert rel in tokens
    ok(partner.age > 32)
    ok(rel.object == partner)
    ok(rel.subject == person)
    ok(rel.type == 'partnership')
    with pytest.raises(IndexError):
        ok(None)

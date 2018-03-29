# flake8: noqa

@pytest.mark.xfail(str("sys.version.find('PyPy') != -1"))
def test_naive_plan_no_join(**kwargs):
    from xoutil.iterators import dict_update_new
    from xotl.ql.translation.py import naive_translation
    select_old_entities = get_query_object(
        who
        for who in Entity
        if who.name.startswith('Manuel')
    )
    dict_update_new(kwargs, dict(only='test_translate.*'))
    plan = naive_translation(select_old_entities, **kwargs)
    result = list(plan())
    assert manu in result
    assert manolito in result
    assert yade not in result


@pytest.mark.xfail(str("sys.version.find('PyPy') != -1"))
def test_ridiculous_join(**kwargs):
    from itertools import product
    from xoutil.iterators import dict_update_new
    from xotl.ql.translation.py import naive_translation
    select_old_entities = get_query_object(
        (who, who2)
        for who in Person
        for who2 in Person
    )
    dict_update_new(kwargs, dict(only='test_translate.*'))
    plan = naive_translation(select_old_entities, **kwargs)
    result = list(plan())
    source = (elsa, manu, denia, pedro, yade, manolito)
    for pair in product(source, source):
        assert pair in result


class B:
    a = [1, 2]


class X:
    def __init__(self):
        self.b = B()


@pytest.mark.xfail(str("sys.version.find('PyPy') != -1"))
def test_traversing_by_nonexistent_attribute(**kwargs):
    from xoutil.iterators import dict_update_new
    from xotl.ql.translation.py import naive_translation
    dict_update_new(kwargs, dict(only='test_translate.*'))

    # There's no `childs` attribute in Persons
    query = get_query_object(
        child
        for parent in Person
        if parent.childs and parent.age > 30
        for child in parent.childs
        if child.age < 10
    )
    plan = naive_translation(query, **kwargs)
    assert list(plan()) == []

    # And much less a `foobar`
    query = get_query_object(parent for parent in Person if parent.foobar)
    plan = naive_translation(query, **kwargs)
    assert list(plan()) == []

    # And traversing through a non-existing stuff doesn't make
    # any sense either, but should not fail
    query = get_query_object(
        foos.name
        for person in Person
        for foos in person.foobars
    )
    plan = naive_translation(query, **kwargs)
    assert list(plan()) == []

    # However either trying to traverse to a second level without testing
    # should fail
    query = get_query_object(a for p in this for a in p.b.a)
    plan = naive_translation(query, **kwargs)
    with pytest.raises(AttributeError):
        list(plan())

    # The same query in a safe fashion
    query = get_query_object(a
                  for p in this
                  if p.b and p.b.a
                  for a in p.b.a)
    plan = naive_translation(query, **kwargs)
    assert list(plan()) == []

    # Now let's rerun the plan after we create some object that matches
    x = X()
    assert list(plan()) == x.b.a


@pytest.mark.xfail(str("sys.version.find('PyPy') != -1"))
def test_token_before_filter():
    query = get_query_object(
        (parent, child)
        for parent in this
        if parent.children
        for child in parent.children
        if child.age < 5
        for dummy in parent.children
    )

    parent, child = query.selection
    parent_token, children_token, dummy_token = query.tokens
    expr1, expr2 = query.filters

    def ok(e1, e2):
        assert e1 == e2
    ok(expr1, parent.children)
    ok(expr2, child.age < 5)

    assert not token_before_filter(children_token, expr1), \
        repr((children_token, expr1, expr2))
    assert token_before_filter(children_token, expr2, True)
    assert token_before_filter(parent_token, expr2, True)
    assert not token_before_filter(dummy_token, expr2, True)


@pytest.mark.xfail(str("sys.version.find('PyPy') != -1"))
def test_regression_test_token_before_filter_20130401():
    query = get_query_object(who
                  for who in Entity
                  if who.name.starswith('Manuel'))
    is_entity_filter, name_filter = query.filters
    token = query.tokens[0]
    assert len(query.tokens) == 1
    assert token_before_filter(token, is_entity_filter, True)
    assert token_before_filter(token, name_filter, True)


@pytest.mark.xfail(str("sys.version.find('PyPy') != -1"))
def test_translation_with_call_of_a_function():
    from xoutil.iterators import zip
    from xotl.ql.translation.py import naive_translation

    @thesefy
    class Universe(int):
        pass
    Universe.this_instances = [
        Universe(i) for i in range(2, 10)] + ['invalid']

    def gcd(a, b):
        while a % b != 0:
            a, b = b, a % b
        return b

    expected = set(
        (a, b)
        for a in range(2, 10)
        for b in range(2, 10)
        if a > b and gcd(a, b) == 1
    )
    assert expected == set([(3, 2),
                            (4, 3),
                            (5, 2), (5, 3), (5, 4),
                            (6, 5),
                            (7, 2), (7, 3), (7, 4), (7, 5), (7, 6),
                            (8, 3), (8, 5), (8, 7),
                            (9, 2), (9, 4), (9, 5), (9, 7), (9, 8)])

    query = get_query_object(
        (a, b)
        for a, b in zip(Universe, Universe)
        if a > b and gcd(a, b) == 1
    )
    plan = naive_translation(query)
    assert set(plan()) == set([(3, 2),
                               (4, 3),
                               (5, 2), (5, 3), (5, 4),
                               (6, 5),
                               (7, 2), (7, 3), (7, 4), (7, 5), (7, 6),
                               (8, 3), (8, 5), (8, 7),
                               (9, 2), (9, 4), (9, 5), (9, 7), (9, 8)])

    query = get_query_object(
        ((a, b)
         for a, b in zip(Universe, Universe)
         if a > b and gcd(a, b) == 1),
        offset=100
    )
    plan = naive_translation(query)
    assert len(list(plan())) == 0


@pytest.mark.xfail(str("sys.version.find('PyPy') != -1"))
def test_ordering():
    from xotl.ql.translation.py import naive_translation

    @thesefy
    class Universe(int):
        pass
    Universe.this_instances = [Universe(i) for i in range(2, 10)]

    query = get_query_object((which for which in Universe),
                             ordering=lambda which: -which)
    plan = naive_translation(query)
    assert list(plan()) == list(reversed(range(2, 10)))

    query = get_query_object((which for which in Universe),
                             ordering=lambda which: +which)
    plan = naive_translation(query)
    assert list(plan()) == list(range(2, 10))  # XXX: Py3k list()

    query = get_query_object((person for person in Person),
                             ordering=lambda person: -person.age)
    plan = naive_translation(query)
    results = list(plan())
    assert manolito == results[-1]
    assert elsa == results[0]

    query = get_query_object((person for person in Person if person.children))
    plan = naive_translation(query)
    results = list(plan())
    parents = (manu, yade, pedro, papi, elsa, ppp, denia)
    for who in parents:
        assert who in results
    assert len(results) == len(parents)

    query = get_query_object(
        (person for person in Person if person.children),
        ordering=lambda person: (
            -sum(child.age for child in person.children),
            -person.age)
    )
    plan = naive_translation(query)
    results = list(plan())
    assert pedro == results[0]


@pytest.mark.xfail(str("sys.version.find('PyPy') != -1"))
def test_short_circuit():
    from xotl.ql import thesefy
    from xotl.ql.translation.py import naive_translation
    from xoutil.eight import integer_types

    integer = integer_types[-1]  # long or int

    flag = [0]   # A list to allow non-global non-local in Py2k

    def inc_flag(by=1):
        flag[0] += 1
        return flag[0]

    @thesefy
    class Universe(integer):
        pass
    Universe.this_instances = [Universe(1780917517912941696167)]

    query = get_query_object(
        atom
        for atom in Universe
        if inc_flag() > 1 and inc_flag()
    )
    plan = naive_translation(query)
    list(plan())
    assert flag[0] == 1

    flag[0] = 0
    query = get_query_object(
        atom
        for atom in Universe
        if inc_flag() > 0 or inc_flag()
    )
    plan = naive_translation(query)
    list(plan())
    assert flag[0] == 1


@pytest.mark.xfail(str("sys.version.find('PyPy') != -1"))
def test_no_custom():
    from xotl.ql.translation.py import naive_translation
    from xotl.ql.expressions import Operator, N_ARITY

    class myoperator(Operator):
        arity = N_ARITY
        _format = 'myoperator({0}{1})'

    query = get_query_object(person for person in Person if myoperator(person))
    with pytest.raises(TypeError):
        plan = naive_translation(query)
        list(plan())


@pytest.mark.xfail(str("sys.version.find('PyPy') != -1"))
def test_query_objects_iteration():
    @thesefy
    class Universe(int):
        pass
    Universe.this_instances = [Universe(i) for i in range(2, 10)]
    query = get_query_object(atom for atom in Universe)
    # XXX: Only for our implementation of QueryObject
    first_plan = getattr(query, '_query_execution_plan', None)
    for atom in Universe.this_instances:
        assert atom in results
    assert len(results) == len(Universe.this_instances)

    again = list(query)
    second_plan  = getattr(query, '_query_execution_plan', None)
    assert len(results) == len(again)

    assert first_plan is second_plan

    from itertools import product
    assert list(product(results, results)) == list(
        product(iter(query), iter(query)))

#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# ---------------------------------------------------------------------
# metamodel
# ---------------------------------------------------------------------
# Copyright (c) 2016 Merchise Autrement and Contributors
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under the
# terms of the LICENCE attached (see LICENCE file) in the distribution
# package.
#
# Created on 2016-03-02

from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)

from xoutil import Unset


# The following classes are just a simple Object Model
class TransitiveRelationDescriptor(object):
    '''A transitive relation.

    :param name:  The name of the attribute.  This must be same name of the
           actual attribute in the class definition.

           We're lazy and don't want to provide a metaclass.

    :param target: A type or None.  If set, you may only set instances of this
           type this attribute.

    '''
    def __init__(self, name, target=None):
        self.name = name
        self.internal_name = '_' + name
        self.target = target

    def __get__(self, instance, cls):
        if instance is None:
            return self
        else:
            result = getattr(instance, self.internal_name, None)
            if result:
                rel = list(result)[0]
                result = [rel]
                children = getattr(rel, self.name, Unset)
                if children is not Unset and children:
                    result.extend(
                        child for child in children if child not in result)
            return result

    def __set__(self, instance, value):
        if value is None:
            try:
                delattr(instance, self.internal_name)
            except:
                pass
        else:
            assert self.target is None or isinstance(value, self.target)
            setattr(instance, self.internal_name, [value])

    def __delete__(self, instance):
        setattr(instance, self.name, None)


class backref(object):
    '''A back-reference descriptor.

    Allows to create back references.  When

    :param name:  The name of the attribute.  Must be the same name.
    :param ref:  The name of the reference in the remote object.

    :param target: A type or None.  If not None, the assigned value must an
                   instance of the type.

    When you assign a value to this kind of attribute, that value object will
    gain an attribute containing a back-reference.  Back references are always
    lists.

    '''
    def __init__(self, name, ref, target=None):
        self.name = name
        self._name = 'backref_%s' % name
        self.ref = ref
        self.target = target

    def __get__(self, inst, cls):
        if not inst:
            return self
        else:
            return getattr(inst, self._name, None)

    def __set__(self, inst, value):
        from xoutil.objects import setdefaultattr
        target = self.target
        if target and not isinstance(value, target):
            raise TypeError('Cannot assign %s to %s' % (value, self.name))
        previous = getattr(inst, self._name, None)
        if previous:
            backrefs = getattr(previous, self.ref)
            backrefs.remove(self)
        setattr(inst, self._name, value)
        backrefs = setdefaultattr(value, self.ref, [])
        backrefs.append(inst)


def date_property(internal_attr_name):
    '''Creates a property date property that accepts string repr of dates

    :param internal_attr_name: The name of the attribute that will be used
                               internally to store the value. It should be
                               different that the name of the property itself.
    '''
    def getter(self):
        return getattr(self, internal_attr_name)

    def setter(self, value):
        from datetime import datetime
        if not isinstance(value, datetime):
            from re import compile
            pattern = compile(r'(\d{4})-(\d{1,2})-(\d{1,2})')
            match = pattern.match(value)
            if match:
                year, month, day = match.groups()
                value = datetime(year=int(year),
                                 month=int(month),
                                 day=int(day))
            else:
                raise ValueError('Invalid date')
        setattr(self, internal_attr_name, value)

    def fdel(self):
        delattr(self, internal_attr_name)

    return property(getter, setter, fdel)


# So that ages are stable in tests
def get_birth_date(age, today=None):
    from datetime import datetime, timedelta
    if today is None:
        today = datetime.today()
    birth = today - timedelta(days=age*365)
    # Brute force
    if get_age(birth, today) == age:
        return birth
    while get_age(birth, today) < age:
        birth += timedelta(days=1)
    while get_age(birth, today) > age:
        birth -= timedelta(days=1)
    return birth


def get_age(birthdate, today=None):
    from datetime import datetime
    if today is None:
        today = datetime.today()
    age = today - birthdate
    return age.days / 365


def age_property(start_attr_name, end_attr_name=None, age_attr_name=None):
    '''Creates a property for calculating the `age` given an
    attribute that holds the starting date of the event.

    :param start_attr_name: The name of the attribute that holds the
                            starting date of the event.
    :param end_attr_name: The name of the attribute that holds the end date
                          of the event. If None, each time `age` is calculated
                          `today` is used as the end date.
    :returns: The age in years (using 365.25 days per year).
    '''
    @property
    def age(self):
        from datetime import datetime
        if not end_attr_name:
            end = datetime.today()
        else:
            end = getattr(self, end_attr_name)
        date = getattr(self, start_attr_name)
        return get_age(date, end)
    return age
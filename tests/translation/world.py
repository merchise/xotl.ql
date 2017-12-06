#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------
# Copyright (c) Merchise Autrement [~º/~] and Contributors
# All rights reserved.
#
# This is free software; you can do what the LICENCE file allows you to.
#

from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)

from .metamodel import get_birth_date
from .model import Person, Place

__all__ = [
    'cuba', 'havana', 'lisa', 'cotorro', 'ciego', 'moron',
    'elsa', 'papi', 'manu', 'denia', 'pedro', 'yade', 'ppp',
    'pedri', 'carli', 'manolito'
]


# TODO:  Make this fixtures
cuba = Place(name='Cuba', type='Country')
havana = Place(name='Havana', type='Province', located_in=cuba)
lisa = Place(name='La lisa', type='Municipality', located_in=havana)
cotorro = Place(name='Cotorro', type='Municipality', located_in=havana)
ciego = Place(name='Ciego de Ávila', type='Province', located_in=cuba)
moron = Place(name='Morón', type='Municipality', located_in=ciego)


elsa = Person(name='Elsa Acosta Cabrera',
              birthdate=get_birth_date(65),
              lives_in=moron)

papi = Person(name='Manuel Vázquez Portal',
              birthdate=get_birth_date(63))

manu = Person(name='Manuel Vázquez Acosta',
              birthdate=get_birth_date(34),
              mother=elsa,
              father=papi,
              lives_in=lisa)

denia = Person(name='Ana Denia Pérez',
               birthdate=get_birth_date(58),
               lives_in=cotorro)

pedro = Person(name='Pedro Piñero',
               birthdate=get_birth_date(60),
               lives_in=cotorro)

yade = Person(name='Yadenis Piñero Pérez',
              birthdate=get_birth_date(33),
              mother=denia,
              father=pedro, lives_in=lisa)

ppp = Person(name='Yobanis Piñero Pérez',
             birthdate=get_birth_date(36),
             mother=denia,
             father=pedro,
             lives_in=lisa)

pedri = Person(name='Pedrito',
               birthdate=get_birth_date(10),
               father=ppp)

carli = Person(name='Carli',
               birthdate=get_birth_date(8),
               father=ppp)

manolito = Person(name='Manuel Vázquez Piñero',
                  birthdate=get_birth_date(6),
                  mother=yade,
                  father=manu,
                  lives_in=lisa)

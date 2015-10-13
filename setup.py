#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------
# setup
# ---------------------------------------------------------------------
# Copyright (c) 2012-2015 Merchise Autrement and Contributors
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under
# the terms of the LICENCE attached in the distribution package.
#
# Created on 2012-06-29


from __future__ import (division as _py3_division,
                        print_function as _py3_print)

import os
import sys
from setuptools import setup, find_packages

# Import the version from the release module
project_name = str('xotl.ql')
_current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(_current_dir, 'xotl', 'ql'))
from release import VERSION as version

setup(
    name=project_name,
    version=version,
    description=("A pythonic query language, with similar goals as "
                 "LINQ had for C#"),
    long_description=open(
        os.path.join(_current_dir, "docs", "readme.txt")).read(),
    # Get more strings from
    # http://pypi.python.org/pypi?:action=list_classifiers
    classifiers=[
        "Programming Language :: Python",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Topic :: Database",
    ],
      keywords=['query language', 'python', 'xotl'],
    author='Merchise Autrement',
    author_email='info@merchise.org',
    url='http://github.com/merchise-autrement/',
    license='GNU General Public License version 3 or later (GPLv3+)',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    namespace_packages=['xotl', ],
    include_package_data=True,
    zip_safe=False,
    setup_requires=['setuptools', ],
    install_requires=[
        'six',
        'xoutil>=1.7.0.dev',
        'zope.interface',
    ],
    extras_require={
        'doc': ['docutils>=0.7',
                'Sphinx>=1.0.7',
                'repoze.sphinx.autointerface>=0.7.0']
    }
)

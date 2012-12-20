#!/usr/bin/env python
# -*- coding: utf-8 -*-
#----------------------------------------------------------------------
# setup
#----------------------------------------------------------------------
# Copyright (c) 2012 Merchise Autrement and Contributors
# All rights reserved.
#
# This is free software; you can redistribute it and/or modify it under
# the terms of the LICENCE attached in the distribution package.
#
# Created on 2012-06-29


from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        unicode_literals as _py3_unicode)
                        # XXX: Don't put absolute imports in setup.py

import os, sys
from setuptools import setup, find_packages

# Import the version from the release module
project_name = 'xotl.ql'
_current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(_current_dir, 'xotl', 'ql'))
from release import VERSION as version

setup(name=project_name,
      version=version,
      description=("A pythonic query language, with similar goals as "
                   "LINQ had for C#"),
      long_description=open(os.path.join("docs", "readme.txt")).read(),
      # Get more strings from
      # http://pypi.python.org/pypi?:action=list_classifiers
      classifiers=[
        "Programming Language :: Python",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Operating System :: OS Independent",
        "Topic :: Database",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
      ],
      keywords=['query language', 'python', 'xotl'],
      author='Merchise Autrement',
      author_email='med.merchise@gmail.com',
      url='http://github.com/merchise-autrement/',
      license='GNU General Public License version 3 or later (GPLv3+)',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      namespace_packages=['xotl', ],
      include_package_data=True,
      zip_safe=False,
      setup_requires=['setuptools', ],
      install_requires=[
          'xoutil>=1.1.4',
          'zope.interface>=3.8.0',
          'zope.component>=3.11.0',

          # For documentation only. But it may be needed for ReadTheDocs
          'repoze.sphinx.autointerface>=0.7.0',
      ],
      extra_requires={
        'doc': ['docutils>=0.7',
                'Sphinx>=1.0.7',
                'repoze.sphinx.autointerface>=0.7.0']
      }
    )

#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------
# Copyright (c) Merchise Autrement [~º/~] and Contributors
# All rights reserved.
#
# This is free software; you can do what the LICENCE file allows you to.
#

# flake8: noqa

from __future__ import (division as _py3_division,
                        print_function as _py3_print)

import os
import sys
from setuptools import Command
from setuptools.command.test import test as TestCommand
from setuptools import setup, find_packages

try:
    execfile = execfile
except NameError:
    def execfile(filename):
        'To run in Python 3'
        import builtins
        exec_ = getattr(builtins, 'exec')
        with open(filename, "rb") as f:
            code = compile(f.read().decode('utf-8'), filename, 'exec')
            return exec_(code, globals())

# Import the version from the release module
project_name = str('xotl.ql')
_current_dir = os.path.dirname(os.path.abspath(__file__))
execfile(os.path.join(_current_dir, 'xotl', 'ql', 'release.py'))

version = VERSION  # noqa

if RELEASE_TAG != '':   # noqa
    dev_classifier = 'Development Status :: 4 - Beta'
else:
    dev_classifier = 'Development Status :: 5 - Production/Stable'


class PyTest(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        # import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main(self.test_args)
        sys.exit(errno)


class PyShell(Command):
    user_options = []

    def initialize_options(self):
        pass

    def ensure_finalized(self):
        pass

    def run(self):
        from IPython import start_ipython
        start_ipython(argv=[''])

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
        dev_classifier,
        "Programming Language :: Python",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Topic :: Database",
    ],
    keywords=['query language', 'python', 'xotl'],
    author='Merchise Autrement',
    author_email='info@merchise.org',
    url='http://github.com/merchise-autrement/',
    license='GNU General Public License version 3 or later (GPLv3+)',
    tests_require=['pytest'],
    cmdclass={'test': PyTest,
              'shell': PyShell},
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    namespace_packages=['xotl', ],
    include_package_data=True,
    zip_safe=False,
    python_requires='>=3.5,<3.7',
    install_requires=[
        'xoutil>=1.9.4',
    ],
    extras_require={
        'doc': [
            'docutils>=0.7',
            'Sphinx>=1.0.7',
        ]
    }
)

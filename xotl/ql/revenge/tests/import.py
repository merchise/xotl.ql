"""
test_import.py -- source test pattern for import statements

This source is part of the decompyle test suite.

decompyle is a Python byte-code decompiler
See http://www.crazy-compilers.com/decompyle/ for
for further information
"""
from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)

import sys
import os, sys, http.server

import test.test_MimeWriter

from rfc822 import Message
from mimetools import Message, decode, choose_boundary
from os import *

for k, v in list(globals().items()):
    print(repr(k), v)

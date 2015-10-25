# extendedImport.py -- source test pattern for extended import statements
#
# This simple program is part of the decompyle test suite.
#
# decompyle is a Python byte-code decompiler
# See http://www.crazy-compilers.com/decompyle/ for
# for further information
from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)

import os, sys as System, time
import sys

from rfc822 import Message as Msg822
from mimetools import Message as MimeMsg, decode, choose_boundary as MimeBoundary

import test.test_StringIO as StringTest

for k, v in list(globals().items()):
    print(repr(k), v)

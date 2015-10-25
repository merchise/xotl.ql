"""
test_import_as.py -- source test pattern for 'import .. as 'statements

This source is part of the decompyle test suite.

decompyle is a Python byte-code decompiler
See http://www.crazy-compilers.com/decompyle/ for
for further information
"""
from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)

import sys as SYS
import os as OS, sys as SYSTEM, http.server as HTTPServ

import test.test_MimeWriter as Mime_Writer

from rfc822 import Message as MSG
from mimetools import Message as mimeMsg, decode, \
     choose_boundary as mimeBoundry

print('---' * 20)

for k, v in list(globals().items()):
    print(k, repr(v))

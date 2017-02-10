# Excerpts from cpython's sphinx extensions to better intergrate with its
# documentation.

from __future__ import absolute_import as _py3_abs_import

import re
from sphinx import addnodes

opcode_sig_re = re.compile(r'(\w+(?:\+\d)?)(?:\s*\((.*)\))?')


def parse_opcode_signature(env, sig, signode):
    """Transform an opcode signature into RST nodes."""
    m = opcode_sig_re.match(sig)
    if m is None:
        raise ValueError
    opname, arglist = m.groups()
    signode += addnodes.desc_name(opname, opname)
    if arglist is not None:
        paramlist = addnodes.desc_parameterlist()
        signode += paramlist
        paramlist += addnodes.desc_parameter(arglist, arglist)
    return opname.strip()


def setup(app):
    app.add_description_unit('opcode', 'opcode', '%s (opcode)',
                             parse_opcode_signature)
    return {'version': '1.0', 'parallel_read_safe': True}

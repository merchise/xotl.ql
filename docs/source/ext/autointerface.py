#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This is taken from repoze.sphinx.autointerface and modified to suite our
# needs

from __future__ import (division as _py3_division,
                        print_function as _py3_print,
                        absolute_import as _py3_abs_import)

from sphinx.util.docstrings import prepare_docstring
from sphinx.util import force_decode
try:
    # Sphinx < 1.0
    from sphinx.directives.desc import ClasslikeDesc as PyClasslike
except ImportError:
    from sphinx.domains.python import PyClasslike
from sphinx.ext import autodoc
from xotl.ql.interfaces import Interface, InterfaceType


class InterfaceDesc(PyClasslike):
    def get_index_text(self, modname, name_cls):
        return '%s (interface in %s)' % (name_cls[0], modname)


class InterfaceDocumenter(autodoc.ClassDocumenter):
    """
    Specialized Documenter directive for zope interfaces.
    """
    objtype = "interface"
    # Must be a higher priority than ClassDocumenter
    member_order = 10

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.options.show_inheritance = True

    @classmethod
    def can_document_member(cls, member, membername, isattr, parent):
        return isinstance(member, InterfaceType)

    def add_directive_header(self, sig):
        if self.doc_as_attr:
            self.directivetype = 'attribute'
        autodoc.Documenter.add_directive_header(self, sig)
        # add inheritance info, if wanted
        bases = [
            base
            for base in self.object.__bases__
            if base is not Interface
        ]
        if not self.doc_as_attr and self.options.show_inheritance and bases:
            self.add_line('', '<autodoc>')
            bases = [':class:`%s.%s`' % (b.__module__, b.__name__)
                     for b in bases]
            self.add_line('   Extends: %s' % ', '.join(bases), '<autodoc>')

    def format_args(self):
        return ""

    def document_members(self, all_members=True):
        oldindent = self.indent
        members = list(self.object.describe())
        if self.options.members is not autodoc.ALL:
            specified = []
            for line in (self.options.members or []):
                specified.extend(line.split())
            mapping = dict(members)
            members = [(x, mapping[x]) for x in specified]
        member_order = (self.options.member_order or
                        self.env.config.autodoc_member_order)
        if member_order == 'alphabetical':
            members.sort()
        if member_order == 'groupwise':
            # sort by group; relies on stable sort to keep items in the
            # same group sorted alphabetically
            members.sort(
                key=lambda e: getattr(e[1], 'signature', None) is not None
            )
        elif member_order == 'bysource' and self.analyzer:
            # sort by source order, by virtue of the module analyzer
            tagorder = self.analyzer.tagorder
            name = self.object.__name__

            def keyfunc(entry):
                return tagorder.get('%s.%s' % (name, entry[0]), len(tagorder))
            members.sort(key=keyfunc)

        for name, desc in members:
            self.add_line('', '<autointerface>')
            sig = desc.signature
            if sig is None:
                self.add_line('.. attribute:: %s' % name, '<autointerface>')
            else:
                self.add_line('.. method:: %s%s' % (name, sig), '<autointerface>')
            doc = desc.doc
            if doc:
                self.add_line('', '<autointerface>')
                self.indent += self.content_indent
                sourcename = 'docstring of %s.%s' % (self.fullname, name)
                docstrings = [prepare_docstring(force_decode(doc, None))]
                for i, line in enumerate(self.process_doc(docstrings)):
                    self.add_line(line, sourcename, i)
                self.add_line('', '<autointerface>')
                self.indent = oldindent


def setup(app):
    app.add_directive_to_domain('py', 'interface', InterfaceDesc)
    app.add_autodocumenter(InterfaceDocumenter)

.. _revenge:
============================================
 Reverse Engineering using an Earley parser
============================================

.. default-role:: term

Starting with version 0.3.0 we are exploring how to get the `query
expression`:term: from the compiled `byte-code`:term: by doing `reverse
engineering`:term:.

This document (however a draft) describes the internal details of this
process.

The goal of the package `xotl.ql.revenge`:mod: is to transform pieces of `byte
code` to an `AST` that is amenable to both transformation and translation.

The `revenge`:mod: package contains the following modules:

`xotl.ql.revenge.scanners`:mod:

   Contains the scanners that split byte-code into tokens.  Those tokens are
   then fed to a parser that "recognizes" the high level instruction from
   those low level.

`xotl.ql.revenge.parsers`:mod:

   Contains the parser that generate a syntax tree that can be used to build
   the high-level AST.

`xotl.ql.revenge.spark`:mod:

   A generic implementation of Early parsers.  Used by
   `xotl.ql.revenge.parsers`:mod:.

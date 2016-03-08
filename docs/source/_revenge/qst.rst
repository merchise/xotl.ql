.. _qst:

===================
 Query Syntax Tree
===================

A `Query Syntax Tree`:term: (QST) is just an *enriched*, but restricted to
expressions, variant of the Abstract Syntax Tree (AST) provided by the
standard `ast`:mod: module.

The change in name obeys the following rationale:

- We don't use the `ast`:mod: objects directly since they don't support
  comparison.  Nevertheless, we'll use the names in that module to express the
  same syntactical element in Query Syntax Trees.

- We don't need any construction that does not appear in expressions, e.g
  `ast.FunctionDef`:class:, `ast.While`:class: and others won't appear in any
  Query Syntax Tree.  Although `ast.Yield` is an expression it is not valid
  within a Query.

- We'd like to emphasize we describe queries and not any kind of program.

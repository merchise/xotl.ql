==========
Known bugs
==========

1. There seems to be a thread-safety bug. Some tests fail "randomly", and
   unless there's no-determinism in our algorithm, that failure should come
   from several threads interacting somehow.


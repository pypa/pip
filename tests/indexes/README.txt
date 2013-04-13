
Details on Test Indexes
=======================

empty_with_pkg
--------------
empty index, but there's a package in the dir

in dex
------
for testing url quoting with indexes

simple
------
contains index page for "simple" pkg

gzipped
-------
not meant to be pip-installed; the index.html is gzipped

iso_8859_1
----------
not meant to be pip-installed; the index.html is encoded as ISO-8859-1
and will raise UnicodeDecodeError when decoded using UTF-8


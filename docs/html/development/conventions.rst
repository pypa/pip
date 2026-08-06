:orphan:

=========================
Documentation Conventions
=========================

This document describes the conventions used in pip's documentation. We
expect it to evolve over time as additional conventions are identified
and past conventions are rendered obsolete.

.. note::

   Currently, these conventions are not enforced automatically, and
   need to be verified manually during code review. We are interested
   in linters that can help us enforce these conventions automatically.


Files
=====

Naming
------

Folder names should be a single word, all lowercase.

File names must use the kebab-case style (all lowercase, hyphen for
separating words) and have the extension ``.rst``.

Encoding
--------

All files in our documentation must use UTF-8 encoding.

Line Length
-----------

Limit all lines to a maximum of 72 characters, where possible. This may
be exceeded when it does not make sense to abide by it (eg. long links,
code blocks).

Headings
========

Use the following symbols to create headings:

#. ``=`` with overline
#. ``=``
#. ``-``
#. ``^``
#. ``'``
#. ``*``

For visual separation from the rest of the content, all other headings
must have one empty line before and after. Heading 2 (``=``) should have
two empty lines before, for indicating the end of the section prior to
it.

::

   =========
   Heading 1
   =========

   Lorem ipsum dolor sit amet consectetur adipisicing elit.


   Heading 2
   =========

   Lorem ipsum dolor sit amet consectetur adipisicing elit.

   Heading 3
   ---------

   Lorem ipsum dolor sit amet consectetur adipisicing elit.

   Heading 4
   ^^^^^^^^^

   Lorem ipsum dolor sit amet consectetur adipisicing elit.

   Heading 5
   '''''''''

   Lorem ipsum dolor sit amet consectetur adipisicing elit.

   Heading 6
   *********

   Lorem ipsum dolor sit amet consectetur adipisicing elit.


Writing
=======

The name of the application (and the project) is "pip". This is a normal noun,
and as such should be capitalised the same as any other noun (uppercase at the
start of a sentence, lowercase within a sentence).

The command name, ``pip`` (generally rendered in a fixed-width font, as
here), is case sensitive and should be rendered in lowercase at all times.
If you find that you need to start a sentence with ``pip`` (the command name),
you should still use lowercase, but it can be better to reword your text to
avoid starting the sentence with the command name. A simple rewording is
to use the phrase "The ``pip`` command...".

.. note::

   Previously, it was a common practice to write "pip" in lowercase in all
   contexts. You may still see that usage in some cases. However, this was
   never the formal project policy, and the advice here supersedes that
   convention.

Avoid using phrases such as "easy", "just", "simply" etc, which imply
that the task is trivial. If it were trivial, the user wouldn't be
reading the documentation for it.

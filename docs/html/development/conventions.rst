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


File Layout
===========

Line Length
-----------

Limit all lines to a maximum of 72 characters, where possible. This may
be exceeded when it does not make sense to abide by it (eg. long links,
code blocks).

Indentation
-----------

We use 3 spaces for indentation.

::

   .. note::

      Directive blocks

   ::

      Code block.

Bullet lists are the only exception to the 3 spaces rule, using 2 spaces
when wrapping lines.

::

   - This is a bullet list.
   - This is a lot of text in a single bullet which would require wrapping
     across multiple lines to fit in the line length limits.

Note that nested lists would use 3 spaces for indentation, and require
blank lines on either side (that's the ReST syntax).

::

   - This is a bullet list.
   - There is a nested list associated with this list item.

      - This is a nested bullet list.
      - With multiple bullets even.
      - And some of the bullets have really long sentences that would
        require wrapping across multiple lines.

   - This is a lot of text in a single bullet which would require wrapping
     across multiple lines to fit in the line length limits.

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

.. note::

   We're still discussing *how* pip should be capitalized in prose. The
   current statement here is tentative.

pip is a proper noun, and spelt all lowercase. Do not capitalize pip as
"Pip" at the start of a sentence.

Avoid using phrases such as "easy", "just", "simply" etc, which imply
that the task is trivial. If it were trivial, the user wouldn't be
reading the documentation for it.

.. _`pip check`:

pip check
---------

.. contents::

Usage
*****

.. pip-command-usage:: check


Description
***********

.. pip-command-description:: check


Examples
********

#. If all dependencies are compatible:

    ::

     $ pip check
     No broken requirements found.
     $ echo $?
     0

#. If a package is missing:

    ::

     $ pip check
     pyramid 1.5.2 requires WebOb, which is not installed.
     $ echo $?
     1

#. If a package has the wrong version:

    ::

     $ pip check
     pyramid 1.5.2 has requirement WebOb>=1.3.1, but you have WebOb 0.8.
     $ echo $?
     1

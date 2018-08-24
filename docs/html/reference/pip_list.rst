.. _`pip list`:

pip list
---------

.. contents::

Usage
*****

.. pip-command-usage:: list

Description
***********

.. pip-command-description:: list

Options
*******

.. pip-command-options:: list

.. pip-index-options::


Examples
********

#. List installed packages.

    ::

     $ pip list
     docutils (0.10)
     Jinja2 (2.7.2)
     MarkupSafe (0.18)
     Pygments (1.6)
     Sphinx (1.2.1)

#. List outdated packages (excluding editables), and the latest version available.

    ::

     $ pip list --outdated
     docutils (Current: 0.10 Latest: 0.11)
     Sphinx (Current: 1.2.1 Latest: 1.2.2)

#. List installed packages with column formatting.

    ::

     $ pip list --format columns
     Package Version
     ------- -------
     docopt  0.6.2
     idlex   1.13
     jedi    0.9.0

#. List outdated packages with column formatting.

    ::

     $ pip list -o --format columns
     Package    Version Latest Type
     ---------- ------- ------ -----
     retry      0.8.1   0.9.1  wheel
     setuptools 20.6.7  21.0.0 wheel

#. List packages that are not dependencies of other packages. Can be combined with
   other options.

    ::

     $ pip list --outdated --not-required
     docutils (Current: 0.10 Latest: 0.11)

#. Use legacy formatting

    ::

     $ pip list --format=legacy
     colorama (0.3.7)
     docopt (0.6.2)
     idlex (1.13)
     jedi (0.9.0)

#. Use json formatting

    ::

     $ pip list --format=json
     [{'name': 'colorama', 'version': '0.3.7'}, {'name': 'docopt', 'version': '0.6.2'}, ...

#. Use freeze formatting

    ::

     $ pip list --format=freeze
     colorama==0.3.7
     docopt==0.6.2
     idlex==1.13
     jedi==0.9.0

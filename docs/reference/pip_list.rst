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

1) List installed packages.

 ::

  $ pip list
  docutils (0.10)
  Jinja2 (2.7.2)
  MarkupSafe (0.18)
  Pygments (1.6)
  Sphinx (1.2.1)

2) List outdated packages (excluding editables), and the latest version available

 ::

  $ pip list --outdated
  docutils (Current: 0.10 Latest: 0.11)
  Sphinx (Current: 1.2.1 Latest: 1.2.2)

3) List installed packages with column formatting.

 ::

  $ pip list --columns
  Package Version
  ------- -------
  docopt  0.6.2
  idlex   1.13
  jedi    0.9.0

4) List outdated packages with column formatting.

 ::

  $ pip list -o --columns
  Package    Version Latest Type
  ---------- ------- ------ -----
  retry      0.8.1   0.9.1  wheel
  setuptools 20.6.7  21.0.0 wheel

5) Do not use column formatting.

 ::

  $ pip list --no-columns
  DEPRECATION: The --no-columns option will be removed in the future.
  colorama (0.3.7)
  docopt (0.6.2)
  idlex (1.13)
  jedi (0.9.0)

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
  Pygments (1.5)
  docutils (0.9.1)
  Sphinx (1.1.2)
  Jinja2 (2.6)

2) List outdated packages (excluding editables), and the latest version available

 ::

  $ pip list --outdated
  docutils (Current: 0.9.1 Latest: 0.10)
  Sphinx (Current: 1.1.2 Latest: 1.1.3)

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

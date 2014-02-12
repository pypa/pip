
.. _`pip freeze`:

pip freeze
-----------

.. contents::

Usage
*****

.. pip-command-usage:: freeze


Description
***********

.. pip-command-description:: freeze


Options
*******

.. pip-command-options:: freeze


Examples
********

1) Generate output suitable for a requirements file.

 ::

  $ pip freeze
  Jinja2==2.6
  Pygments==1.5
  Sphinx==1.1.3
  docutils==0.9.1


2) Generate a requirements file and then install from it in another environment.

 ::

  $ env1/bin/pip freeze > requirements.txt
  $ env2/bin/pip install -r requirements.txt

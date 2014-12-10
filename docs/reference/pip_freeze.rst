
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
  docutils==0.11
  Jinja2==2.7.2
  MarkupSafe==0.19
  Pygments==1.6
  Sphinx==1.2.2


2) Generate a requirements file and then install from it in another environment.

 ::

  $ env1/bin/pip freeze > requirements.txt
  $ env2/bin/pip install -r requirements.txt

3) Generate output for a single package only.

 ::

  $ pip freeze Jinja2
  Jinja2==2.7.2

4) Generate output for a subset of packages only.

 ::

  $ pip freeze Jinja2 docutils
  docutils==0.11
  Jinja2==2.7.2

5) Generate output for a subset of packages and their (recursive) dependencies.

 ::

  $ pip freeze --recursive Jinja2
  Jinja2==2.7.2
  MarkupSafe==0.19

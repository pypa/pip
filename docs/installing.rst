.. _`Installation`:

Installation
============

Do I need to install pip?
-------------------------

pip is already installed if you're using Python 2 >=2.7.9 or Python 3 >=3.4
downloaded from `python.org <https://www.python.org>`_, but you'll need to
:ref:`upgrade pip <Upgrading pip>`.

Additionally, pip will already be installed if you're working in a :ref:`Virtual
Envionment <pypug:Creating and using Virtual Environments>` created by
:ref:`pypug:virtualenv` or :ref:`pyvenv <pypug:venv>`.


.. _`get-pip`:

Installing with get-pip.py
--------------------------

To install pip, securely download `get-pip.py
<https://bootstrap.pypa.io/get-pip.py>`_. [2]_

Then run the following:

::

 python get-pip.py


.. warning::

   Be cautious if you're using a Python install that's managed by your operating
   system or another package manager. get-pip.py does not coordinate with
   those tools, and may leave your system in an inconsistent state.

get-pip.py will also intall :ref:`pypug:setuptools` [3]_ and :ref:`pypug:wheel`,
if they're not already. :ref:`pypug:setuptools` is required to install
:term:`source distributions <pypug:Source Distribution (or "sdist")>`.  Both are
required to be able to build a :ref:`Wheel cache` (which improves installation
speed), although neither are required to install pre-built :term:`wheels
<pypug:Wheel>`.


get-pip.py options
~~~~~~~~~~~~~~~~~~~

.. option:: --no-setuptools

    If set, don't attempt to install :ref:`pypug:setuptools`

.. option:: --no-wheel

    If set, don't attempt to install :ref:`pypug:wheel`


Additionally, ``get-pip.py`` supports using the :ref:`pip install options <pip
install Options>` and the :ref:`general options <General Options>`. Below are
some examples:

Install from local copies of pip and setuptools::

  python get-pip.py --no-index --find-links=/local/copies

Install to the user site [4]_::

  python get-pip.py --user

Install behind a proxy::

  python get-pip.py --proxy="[user:passwd@]proxy.server:port"


Using Linux Package Managers
----------------------------

See :ref:`pypug:Installing pip/setuptools/wheel with Linux Package Managers` in
the `Python Packaging User Guide
<https://packaging.python.org/en/latest/current/>`_.

.. _`Upgrading pip`:

Upgrading pip
-------------

On Linux or OS X:

::

 pip install -U pip


On Windows [5]_:

::

 python -m pip install -U pip


Python and OS Compatibility
---------------------------

pip works with CPython versions 2.6, 2.7, 3.3, 3.4, 3.5 and also pypy.

This means pip works on the latest patch version of each of these minor versions
(i.e. 2.6.9 for 2.6, etc).
Previous patch versions are supported on a best effort approach.

pip works on Unix/Linux, OS X, and Windows.


----

.. [1] For Python 2, see https://docs.python.org/2/installing, and for Python3,
       see https://docs.python.org/3/installing.

.. [2] "Secure" in this context means using a modern browser or a
       tool like `curl` that verifies SSL certificates when downloading from
       https URLs.

.. [3] Beginning with pip v1.5.1, ``get-pip.py`` stopped requiring setuptools to
       be installed first.

.. [4] The pip developers are considering making ``--user`` the default for all
       installs, including ``get-pip.py`` installs of pip, but at this time,
       ``--user`` installs for pip itself, should not be considered to be fully
       tested or endorsed. For discussion, see `Issue 1668
       <https://github.com/pypa/pip/issues/1668>`_.

.. [5] https://github.com/pypa/pip/issues/1299

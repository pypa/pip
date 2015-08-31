.. _`Installation`:

Installation
============

Do I need to install pip?
-------------------------

Distributions of Python 2.7.9 and later (in the Python 2 series), and
Python 3.4 and later (in the Python 3 series) may already include pip by
default. [1]_

Additionally, it's common to be working in a :ref:`Virtual Envionment
<pypug:Creating and using Virtual Environments>` created by a tool like
:ref:`pypug:virtualenv` or :ref:`pyvenv <pypug:venv>`, which handles installing
pip for you.


.. _`get-pip`:

Installing with get-pip.py
--------------------------

To install pip, securely download `get-pip.py
<https://bootstrap.pypa.io/get-pip.py>`_. [2]_

Then run the following (which may require sudo or administrator access):

::

 python get-pip.py


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


Installing with Linux Package Managers
--------------------------------------

Fedora
~~~~~~

To get the version supplied by the distribution:

* < Fedora 23:

 * Python 2: ``sudo yum install python-pip``
 * Python 3: ``sudo yum install python3-pip``

* >= Fedora 23:

 * Python 2: ``sudo dnf install python-pip``
 * Python 3: ``sudo dnf install python3-pip``

To get newer versions of pip (and also setuptools and wheel), you can enable the
"unofficial" `PyPA Copr Repo <https://copr.fedoraproject.org/coprs/pypa/pypa/>`_
using `these instructions
<https://fedorahosted.org/copr/wiki/HowToEnableRepo>`__, and run the same
commands as above.


CentOS/RHEL
~~~~~~~~~~~

CentOS and RHEL don't offer ``python-pip`` in their core repositories.

It's common practice to install pip from the `EPEL repository
<https://fedoraproject.org/wiki/EPEL>`_. Enable EPEL using `these instructions
<https://fedoraproject.org/wiki/EPEL#How_can_I_use_these_extra_packages.3F>`__,
and install like so::

   sudo yum install python-pip

You can also use the "unofficial" `PyPA Copr Repo
<https://copr.fedoraproject.org/coprs/pypa/pypa/>`_ using `these instructions
<https://fedorahosted.org/copr/wiki/HowToEnableRepo>`__ [5]_, and run the same
command as above.  The Copr repository has an advantage over EPEL in that it
also maintains packages of ``python-wheel`` and newer versions of
``python-setuptools``.

Lastly, If you're using the `IUS repository
<https://iuscommunity.org/pages/Repos.html>`_ to install alternative Python
versions, be aware that IUS also maintains packages for newer versions of pip,
setuptools, and wheel that are consistent with the alternative Python versions.
The IUS packages will not work with the system Python.



Debian/Ubuntu
~~~~~~~~~~~~~

To get the version supplied by the distribution:

::

   sudo apt-get install python-pip


Upgrading
---------

On Linux or OS X:

::

 pip install -U pip


On Windows [5]_:

::

 python -m pip install -U pip


Python and OS Compatibility
---------------------------

pip works with CPython versions 2.6, 2.7, 3.2, 3.3, 3.4, 3.5 and also pypy.

pip works on Unix/Linux, OS X, and Windows.

.. note::

  Python 2.5 was supported through v1.3.1, and Python 2.4 was supported through
  v1.1.


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

.. [5] Currently, there is no "copr" yum plugin available for CentOS/RHEL, so
       the only option is to manually place the repo files as described.

.. [6] https://github.com/pypa/pip/issues/1299

Allow ``--no-use-pep517`` to be used as a work-around when installing a
project in editable mode, even when `PEP 517
<https://www.python.org/dev/peps/pep-0517/>`_ mandates
``pyproject.toml``-style processing (i.e. when the project has a
``pyproject.toml`` file as well as a ``"build-backend"`` key for the
``"build_system"`` value). Since this option conflicts with the PEP 517 spec,
this mode of operation is officially unsupported.

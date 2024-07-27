Upgrade setuptools to 70.3.0

Additionally, remove the suppressed deprecation warning from the vendored
``pkg_resources`` copy to ensure builds succeed with ``PYTHONWARNINGS=error``.

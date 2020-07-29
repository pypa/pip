Add a beta version of pip's next-generation dependency resolver.

Move pip's new resolver into beta, remove the
``--unstable-feature=resolver`` flag, and enable the
``--use-feature=2020-resolver`` flag. The new resolver is
significantly stricter and more consistent when it receives
incompatible instructions, and reduces support for certain kinds of
:ref:`Constraints Files`, so some workarounds and workflows may
break. More details about how to test and migrate, and how to report
issues, at :ref:`Resolver changes 2020` . Maintainers are preparing to
release pip 20.3, with the new resolver on by default, in October.

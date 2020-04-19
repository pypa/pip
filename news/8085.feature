Add a ``--prefer-minimum-versions`` command line flag to tell pip to
use older versions instead of newer versions for all
dependencies. This is useful for running test suites using the "lower
bounds" of requirements to ensure that they are accurate. The flag is
only available when the new resolver is enabled.

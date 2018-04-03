Add public, supported replacement for `pip.main` which uses
`subprocess.check_call` to invoke
  ${sys.executable} -m pip ...
with the given arguments. e.g. `pip.main('install', '-U', 'setuptools')` is now
supported usage.

This means that the behavior may be different from `pip.main` on `pip<10.0.0`.

# Security Policy

## Reporting a Vulnerability

Please read the guidelines on reporting security issues [on the
official website](https://www.python.org/dev/security/) for
instructions on how to report a security-related problem to
the Python Security Response Team responsibly.

To reach the response team, email `security@python.org`.

Pip relies on the Python Security Response Team (PSRT) to triage
and respond to security reports. PSRT members balance security
work against many other responsibilities, so please be thoughtful
about the time and attention your report requires. Reports that
repeatedly disregard this policy may be rejected regardless of
technical merit.

## What pip is expected to do with wheels

Pip downloads a wheel
([binary distribution](https://packaging.python.org/en/latest/specifications/binary-distribution-format/))
by saving it as a file in the target directory, and installs a
wheel by unpacking it into the target environment. If pip runs
code from a wheel while downloading or installing it, or writes
files outside the target directory, that should be reported.

## What is not a pip vulnerability

Due to the design of the Python packaging ecosystem, pip has no way
to know whether an index or a package is malicious, and packages can
run code both while being built and after being installed. The
following are not pip vulnerabilities:

- A malicious or compromised package index.
- A malicious package. Building a package from source runs the build
  tool the package itself chooses
  ([PEP 517](https://peps.python.org/pep-0517/)). Installing a
  wheel does not run code from it, but once any package is
  installed, its code can run whenever Python runs in that
  environment. Report malicious packages on PyPI through
  its [malware reporting process](https://pypi.org/security/).
- An attacker who already controls the machine pip runs on. Anyone
  who can change pip's command line, environment variables,
  configuration, or cache can already make pip install anything.

A bug in a step that already runs arbitrary code is also not a
vulnerability and can be reported as a normal bug on the
[issue tracker](https://github.com/pypa/pip/issues). Any ideas
for improving the security of these processes can be reported
as feature requests.

## Vendored libraries

Pip ships its own copies of its dependencies in `pip/_vendor`. A
vulnerability in one of them is not a vulnerability in pip unless
pip's use of the library is affected. Report the library's bug to
that library's project.

Updates to vendored libraries, including security fixes, are
defined in pip's [release process](https://pip.pypa.io/en/stable/development/release-process/#release-cadence).

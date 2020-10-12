# This value is used in the requests user agent.
# setup.py has it hard-coded separately.
# Currently, when the version is changed, it must be set in both locations.
# TODO: Single-source the version number.
__version__ = "0.15.0"

# This reference implementation produces metadata intended to conform to
# version 1.0.0 of the TUF specification, and is expected to consume metadata
# conforming to version 1.0.0 of the TUF specification.
# All downloaded metadata must be equal to our supported major version of 1.
# For example, "1.4.3" and "1.0.0" are supported.  "2.0.0" is not supported.
# See https://github.com/theupdateframework/specification
SPECIFICATION_VERSION = '1.0.0'

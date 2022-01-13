# Expose a limited set of classes and functions so callers outside of
# the cloudstorage package don't need to import deeper than
# `pip._internal.cloudstorage`.
# (The test directory may still need to import from a vcs sub-package.)
# Import all cloudstorage modules to register each Cloud Storage Provider
# in the CloudStorageSupport object.
import pip._internal.cloudstorage.aws  # noqa: F401
import pip._internal.cloudstorage.gcp  # noqa: F401
from pip._internal.cloudstorage.cloudstorage import cloudstorage  # noqa: F401

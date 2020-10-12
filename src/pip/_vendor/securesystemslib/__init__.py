import logging

# Configure a basic 'securesystemslib' top-level logger with a StreamHandler
# (print to console) and the WARNING log level (print messages of type
# warning, error or critical). This is similar to what 'logging.basicConfig'
# would do with the root logger. All 'securesystemslib.*' loggers default to
# this top-level logger and thus may be configured (e.g. formatted, silenced,
# etc.) with it. It can be accessed via logging.getLogger('securesystemslib').
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)
logger.addHandler(logging.StreamHandler())


# Global constants
# TODO: Replace hard-coded key types with these constants (and add more)
KEY_TYPE_RSA = "rsa"
KEY_TYPE_ED25519 = "ed25519"
KEY_TYPE_ECDSA = "ecdsa"

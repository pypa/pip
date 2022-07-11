import platform
import os
import warnings

from ...backend import KeyringBackend
from ...errors import PasswordSetError
from ...errors import PasswordDeleteError
from ...errors import KeyringLocked
from ...errors import KeyringError
from ...util import properties

try:
    from . import api
except Exception:
    pass


class Keyring(KeyringBackend):
    """macOS Keychain"""

    keychain = os.environ.get('KEYCHAIN_PATH')
    "Path to keychain file, overriding default"

    @properties.ClassProperty
    @classmethod
    def priority(cls):
        """
        Preferred for all macOS environments.
        """
        if platform.system() != 'Darwin':
            raise RuntimeError("macOS required")
        if 'api' not in globals():
            raise RuntimeError("Security API unavailable")
        return 5

    def set_password(self, service, username, password):
        if username is None:
            username = ''

        try:
            api.set_generic_password(self.keychain, service, username, password)
        except api.KeychainDenied as e:
            raise KeyringLocked("Can't store password on keychain: " "{}".format(e))
        except api.Error as e:
            raise PasswordSetError("Can't store password on keychain: " "{}".format(e))

    def get_password(self, service, username):
        if username is None:
            username = ''

        try:
            return api.find_generic_password(self.keychain, service, username)
        except api.NotFound:
            pass
        except api.KeychainDenied as e:
            raise KeyringLocked("Can't get password from keychain: " "{}".format(e))
        except api.Error as e:
            raise KeyringError("Can't get password from keychain: " "{}".format(e))

    def delete_password(self, service, username):
        if username is None:
            username = ''

        try:
            return api.delete_generic_password(self.keychain, service, username)
        except api.Error as e:
            raise PasswordDeleteError(
                "Can't delete password in keychain: " "{}".format(e)
            )

    def with_keychain(self, keychain):
        warnings.warn(
            "macOS.Keyring.with_keychain is deprecated. Use with_properties instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.with_properties(keychain=keychain)

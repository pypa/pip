import logging

logger = logging.getLogger(__name__)

try:
    import keyring  # noqa
except ImportError:
    keyring = None
except Exception as exc:
    logger.warning("Keyring is skipped due to an exception: %s",
                   str(exc))
    keyring = None


def get_keyring_auth(url, username):
    """Return the tuple auth for a given url from keyring."""
    if not url or not keyring:
        return None

    try:
        try:
            get_credential = keyring.get_credential
        except AttributeError:
            pass
        else:
            logger.debug("Getting credentials from keyring for %s", url)
            cred = get_credential(url, username)
            if cred is not None:
                return cred.username, cred.password
            return None

        if username:
            logger.debug("Getting password from keyring for %s", url)
            password = keyring.get_password(url, username)
            if password:
                return username, password

    except Exception as exc:
        logger.warning("Keyring is skipped due to an exception: %s",
                       str(exc))

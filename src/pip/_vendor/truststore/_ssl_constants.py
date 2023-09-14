import ssl

# Hold on to the original class so we can create it consistently
# even if we inject our own SSLContext into the ssl module.
_original_SSLContext = ssl.SSLContext
_original_super_SSLContext = super(_original_SSLContext, _original_SSLContext)


def _set_ssl_context_verify_mode(
    ssl_context: ssl.SSLContext, verify_mode: ssl.VerifyMode
) -> None:
    _original_super_SSLContext.verify_mode.__set__(ssl_context, verify_mode)  # type: ignore[attr-defined]

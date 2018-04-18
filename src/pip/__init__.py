__version__ = "10.0.0"


def main(*args, **kwargs):
    """
    This is an importable main func.
    Its only purpose is to raise a clean error for users who call `pip.main()`
    -- a usage which was never supported.
    """
    raise RuntimeError(
        "pip.main() is unsupported and should not be used. "
        "If you want to invoke pip from within your program, see the "
        "documentation here: "
        "https://pip.pypa.io/en/latest/user_guide/#using-pip-from-your-program"
        "\n"
        "You may find that pip.main() works on pip<10, but pip cannot and "
        "does not support or condone such usage.")

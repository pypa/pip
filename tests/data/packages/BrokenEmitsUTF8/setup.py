# -*- coding: utf-8 -*-

import sys
from distutils.core import setup


class FakeError(Exception):
    pass


if sys.argv[1] == "install":
    if hasattr(sys.stdout, "buffer"):
        sys.stdout.buffer.write(
            "\nThis package prints out UTF-8 stuff like:\n".encode("utf-8")
        )
        sys.stdout.buffer.write(
            "* return type of ‘main’ is not ‘int’\n".encode("utf-8")
        )
        sys.stdout.buffer.write(
            "* Björk Guðmundsdóttir [ˈpjœr̥k ˈkvʏðmʏntsˌtoʊhtɪr]".encode("utf-8")
        )
    else:
        pass
        sys.stdout.write("\nThis package prints out UTF-8 stuff like:\n")
        sys.stdout.write(
            "* return type of \xe2\x80\x98main\xe2\x80\x99 is not \xe2\x80\x98int\xe2\x80\x99\n"
        )
        sys.stdout.write(
            "* Bj\xc3\xb6rk Gu\xc3\xb0mundsd\xc3\xb3ttir [\xcb\x88pj\xc5\x93r\xcc\xa5k \xcb\x88kv\xca\x8f\xc3\xb0m\xca\x8fnts\xcb\x8cto\xca\x8aht\xc9\xaar]\n"
        )

    raise FakeError("this package designed to fail on install")

setup(
    name="broken",
    version="0.2",
    py_modules=["broken"],
)

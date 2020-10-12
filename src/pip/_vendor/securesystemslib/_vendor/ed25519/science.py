# ed25519.py - Optimized version of the reference implementation of Ed25519
#
# Written in 2011? by Daniel J. Bernstein <djb@cr.yp.to>
#            2013 by Donald Stufft <donald@stufft.io>
#            2013 by Alex Gaynor <alex.gaynor@gmail.com>
#            2013 by Greg Price <price@mit.edu>
#
# To the extent possible under law, the author(s) have dedicated all copyright
# and related and neighboring rights to this software to the public domain
# worldwide. This software is distributed without any warranty.
#
# You should have received a copy of the CC0 Public Domain Dedication along
# with this software. If not, see
# <http://creativecommons.org/publicdomain/zero/1.0/>.
import os
import timeit

import ed25519


seed = os.urandom(32)

data = b"The quick brown fox jumps over the lazy dog"
private_key = seed
public_key = ed25519.publickey_unsafe(seed)
signature = ed25519.signature_unsafe(data, private_key, public_key)

print('\nTime verify signature')
print(
    timeit.timeit(
        "ed25519.checkvalid(signature, data, public_key)",
        setup="from __main__ import ed25519, signature, data, public_key",
        number=100,
    )
)

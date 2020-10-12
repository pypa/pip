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
import binascii
import codecs
import os

import pytest

import ed25519


def ed25519_known_answers():
    # Known answers taken from: http://ed25519.cr.yp.to/python/sign.input
    # File Format is a lined based file where each line has sk, pk, m, sm
    #   - Each field hex
    #   - Each field colon-terminated
    #   - sk includes pk at end
    #   - sm includes m at end
    path = os.path.join(os.path.dirname(__file__), "test_data", "ed25519")
    with codecs.open(path, "r", encoding="utf-8") as fp:
        for line in fp:
            x = line.split(":")
            yield (
                # Secret Key
                # Secret key is 32 bytes long, or 64 hex characters and has
                #   public key appended to it
                x[0][0:64].encode("ascii"),
                # Public Key
                x[1].encode("ascii"),
                # Message
                x[2].encode("ascii"),
                # Signed Message
                x[3].encode("ascii"),
                # Signature Only
                # Signature comes from the Signed Message, it is 32 bytes long
                #   and has the message appended to it
                binascii.hexlify(
                    binascii.unhexlify(x[3].encode("ascii"))[:64]
                ),
            )


@pytest.mark.parametrize(
    ("secret_key", "public_key", "message", "signed", "signature"),
    ed25519_known_answers(),
)
def test_ed25519_kat(secret_key, public_key, message, signed, signature):
    sk = binascii.unhexlify(secret_key)
    m = binascii.unhexlify(message)

    pk = ed25519.publickey_unsafe(sk)
    sig = ed25519.signature_unsafe(m, sk, pk)

    # Assert that the signature and public key are what we expected
    assert binascii.hexlify(pk) == public_key
    assert binascii.hexlify(sig) == signature

    # Validate the signature using the checkvalid routine
    ed25519.checkvalid(sig, m, pk)

    # Assert that we cannot forge a message
    try:
        if len(m) == 0:
            forgedm = b"x"
        else:
            forgedm = ed25519.intlist2bytes([
                ed25519.indexbytes(m, i) + (i == len(m) - 1)
                for i in range(len(m))
            ])
    except ValueError:
        # TODO: Yes this means that we "pass" a test if we can't generate a
        # forged message. This matches the original test suite, it's
        # unclear if it was intentional there or not.
        pass
    else:
        with pytest.raises(ed25519.SignatureMismatch):
            ed25519.checkvalid(sig, forgedm, pk)


def test_checkparams():
    # Taken from checkparams.py from DJB
    assert ed25519.b >= 10
    assert 8 * len(ed25519.H(b"hash input")) == 2 * ed25519.b
    assert pow(2, ed25519.q - 1, ed25519.q) == 1
    assert ed25519.q % 4 == 1
    assert pow(2, ed25519.l - 1, ed25519.l) == 1
    assert ed25519.l >= 2 ** (ed25519.b - 4)
    assert ed25519.l <= 2 ** (ed25519.b - 3)
    assert pow(ed25519.d, (ed25519.q - 1) // 2, ed25519.q) == ed25519.q - 1
    assert pow(ed25519.I, 2, ed25519.q) == ed25519.q - 1
    assert ed25519.isoncurve(ed25519.B)
    x, y, z, t = P = ed25519.scalarmult(ed25519.B, ed25519.l)
    assert ed25519.isoncurve(P)
    assert (x, y) == (0, z)

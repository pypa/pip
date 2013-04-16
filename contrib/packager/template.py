#! /usr/bin/env python

sources = """
@SOURCES@"""

import codecs
import os
import sys
import base64
import bz2
import tempfile
import shutil

# quoted-printable is poorly supported on Python 3,
# use the codecs module directly
quopri_decode = codecs.getdecoder('quopri_codec')

def unpack(sources):
    temp_dir = tempfile.mkdtemp('-scratchdir', 'unpacker-')
    for package, content in sources.items():
        filepath = package.split("/")
        dirpath = os.sep.join(filepath[:-1])
        packagedir = os.path.join(temp_dir, dirpath)
        if not os.path.isdir(packagedir):
            os.makedirs(packagedir)
        mod = open(os.path.join(packagedir, filepath[-1]), 'wb')
        try:
            mod.write(quopri_decode(content.encode('ascii'))[0])
        finally:
            mod.close()
    return temp_dir


if __name__ == "__main__":
    if sys.version_info >= (3, 0):
        exec("def do_exec(co, loc): exec(co, loc)\n")
        import pickle
        sources = sources.encode("ascii") # ensure bytes
        sources = pickle.loads(bz2.decompress(base64.decodebytes(sources)))
    else:
        import cPickle as pickle
        exec("def do_exec(co, loc): exec co in loc\n")
        sources = pickle.loads(bz2.decompress(base64.decodestring(sources)))

    try:
        temp_dir = unpack(sources)
        sys.path.insert(0, temp_dir)

        entry = """@ENTRY@"""
        do_exec(entry, locals())
    finally:
        shutil.rmtree(temp_dir)

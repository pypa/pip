#! /usr/bin/env python

# Hi There!
# You may be wondering what this giant blob of binary data here is, you might
# even be worried that we're up to something nefarious (good for you for being
# paranoid!). It is a base64 encoded bz2 stream that was stored using the
# pickle module.
#
# Pip is a thing that installs packages, pip itself is a package that someone
# might want to install, especially if they're looking to run this get-pip.py
# script. Pip has a lot of code to deal with the security of installing
# packages, various edge cases on various platforms, and other such sort of
# "tribal knowledge" that has been encoded in it's code base. Because of this
# we basically include an entire copy of pip inside this blob. We do this
# because the alternatives are attempt to implement a "minipip" that probably
# doesn't do things correctly and has weird edge cases, or compress pip itself
# down into a single file.
#
# If you're wondering how this is created, the secret is
# "contrib/build-installer" from the pip repository.
sources = """
@SOURCES@"""

import codecs
import os
import sys
import base64
import bz2
import tempfile
import shutil

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
            mod.write(base64.b64decode(content))
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

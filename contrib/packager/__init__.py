# Port of Ronny Pfannschmidt's genscript package
# https://bitbucket.org/RonnyPfannschmidt/genscript

import sys
import pickle
import zlib
import base64
import os
import fnmatch


def find_toplevel(name):
    for syspath in sys.path:
        lib = os.path.join(syspath, name)
        if os.path.isdir(lib):
            return lib
        mod = lib + '.py'
        if os.path.isfile(mod):
            return mod
    raise LookupError(name)


def pkgname(toplevel, rootpath, path):
    parts = path.split(os.sep)[len(rootpath.split(os.sep)):]
    return '.'.join([toplevel] + [os.path.splitext(x)[0] for x in parts])


def pkg_to_mapping(name):
    toplevel = find_toplevel(name)
    if os.path.isfile(toplevel):
        return {name: toplevel.read()}

    name2src = {}
    for root, dirs, files in os.walk(toplevel):
        for pyfile in files:
            if fnmatch.fnmatch(pyfile, '*.py'):
                pkg = pkgname(name, toplevel, os.path.join(root, pyfile))
                f = open(os.path.join(root, pyfile))
                try:
                    name2src[pkg] = f.read()
                finally:
                    f.close()
    return name2src


def compress_mapping(mapping):
    data = pickle.dumps(mapping, 2)
    data = zlib.compress(data, 9)
    data = base64.encodestring(data)
    data = data.decode('ascii')
    return data


def compress_packages(names):
    mapping = {}
    for name in names:
        mapping.update(pkg_to_mapping(name))
    return compress_mapping(mapping)


def generate_script(entry, packages):
    data = compress_packages(packages)
    tmpl = open(os.path.join(os.path.dirname(__file__), 'template.py'))
    exe = tmpl.read()
    tmpl.close()
    exe = exe.replace('@SOURCES@', data)
    exe = exe.replace('@ENTRY@', entry)
    return exe

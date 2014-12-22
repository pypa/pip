import base64
import io
import os
import shutil
import tempfile
import zipfile

import invoke

from . import paths


@invoke.task
def authors():
    print("[generate.authors] Generating AUTHORS")

    # Get our list of authors
    print("[generate.authors] Collecting author names")
    r = invoke.run("git log --use-mailmap --format'=%aN <%aE>'", hide=True)
    authors = []
    seen_authors = set()
    for author in r.stdout.splitlines():
        author = author.strip()
        if author.lower() not in seen_authors:
            seen_authors.add(author.lower())
            authors.append(author)

    # Sort our list of Authors by their case insensitive name
    authors = sorted(authors, key=lambda x: x.lower())

    # Write our authors to the AUTHORS file
    print("[generate.authors] Writing AUTHORS")
    with io.open("AUTHORS.txt", "w", encoding="utf8") as fp:
        fp.write(u"\n".join(authors))
        fp.write(u"\n")


@invoke.task
def installer(installer_path=os.path.join(paths.CONTRIB, "get-pip.py")):
    print("[generate.installer] Generating installer")

    # Define our wrapper script
    WRAPPER_SCRIPT = """
#!/usr/bin/env python
#
# Hi There!
# You may be wondering what this giant blob of binary data here is, you might
# even be worried that we're up to something nefarious (good for you for being
# paranoid!). This is a base64 encoding of a zip file, this zip file contains
# an entire copy of pip.
#
# Pip is a thing that installs packages, pip itself is a package that someone
# might want to install, especially if they're looking to run this get-pip.py
# script. Pip has a lot of code to deal with the security of installing
# packages, various edge cases on various platforms, and other such sort of
# "tribal knowledge" that has been encoded in its code base. Because of this
# we basically include an entire copy of pip inside this blob. We do this
# because the alternatives are attempt to implement a "minipip" that probably
# doesn't do things correctly and has weird edge cases, or compress pip itself
# down into a single file.
#
# If you're wondering how this is created, it is using an invoke task located
# in tasks/generate.py called "installer". It can be invoked by using
# ``invoke generate.installer``.

import os.path
import pkgutil
import shutil
import sys
import struct
import tempfile

# Useful for very coarse version differentiation.
PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3

if PY3:
    iterbytes = iter
else:
    def iterbytes(buf):
        return (ord(byte) for byte in buf)

try:
    from base64 import b85decode
except ImportError:
    _b85alphabet = (b"0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                    b"abcdefghijklmnopqrstuvwxyz!#$%&()*+-;<=>?@^_`{{|}}~")

    def b85decode(b):
        _b85dec = [None] * 256
        for i, c in enumerate(iterbytes(_b85alphabet)):
            _b85dec[c] = i

        padding = (-len(b)) % 5
        b = b + b'~' * padding
        out = []
        packI = struct.Struct('!I').pack
        for i in range(0, len(b), 5):
            chunk = b[i:i + 5]
            acc = 0
            try:
                for c in iterbytes(chunk):
                    acc = acc * 85 + _b85dec[c]
            except TypeError:
                for j, c in enumerate(iterbytes(chunk)):
                    if _b85dec[c] is None:
                        raise ValueError('bad base85 character at position %d'
                                        % (i + j))
                raise
            try:
                out.append(packI(acc))
            except struct.error:
                raise ValueError('base85 overflow in hunk starting at byte %d'
                                 % i)

        result = b''.join(out)
        if padding:
            result = result[:-padding]
        return result


def bootstrap(tmpdir=None):
    # Import pip so we can use it to install pip and maybe setuptools too
    import pip

    # We always want to install pip
    packages = ["pip"]

    # Check if the user has requested us not to install setuptools
    if "--no-setuptools" in sys.argv or os.environ.get("PIP_NO_SETUPTOOLS"):
        args = [x for x in sys.argv[1:] if x != "--no-setuptools"]
    else:
        args = sys.argv[1:]

        # We want to see if setuptools is available before attempting to
        # install it
        try:
            import setuptools  # noqa
        except ImportError:
            packages += ["setuptools"]

    delete_tmpdir = False
    try:
        # Create a temporary directory to act as a working directory if we were
        # not given one.
        if tmpdir is None:
            tmpdir = tempfile.mkdtemp()
            delete_tmpdir = True

        # We need to extract the SSL certificates from requests so that they
        # can be passed to --cert
        cert_path = os.path.join(tmpdir, "cacert.pem")
        with open(cert_path, "wb") as cert:
            cert.write(pkgutil.get_data("pip._vendor.requests", "cacert.pem"))

        # Use an environment variable here so that users can still pass
        # --cert via sys.argv
        os.environ.setdefault("PIP_CERT", cert_path)

        # Execute the included pip and use it to install the latest pip and
        # setuptools from PyPI
        sys.exit(pip.main(["install", "--upgrade"] + packages + args))
    finally:
        # Remove our temporary directory
        if delete_tmpdir and tmpdir:
            shutil.rmtree(tmpdir, ignore_errors=True)


def main():
    tmpdir = None
    try:
        # Create a temporary working directory
        tmpdir = tempfile.mkdtemp()

        # Unpack the zipfile into the temporary directory
        pip_zip = os.path.join(tmpdir, "pip.zip")
        with open(pip_zip, "wb") as fp:
            fp.write(b85decode(DATA.replace(b"\\n", b"")))

        # Add the zipfile to sys.path so that we can import it
        sys.path.insert(0, pip_zip)

        # Run the bootstrap
        bootstrap(tmpdir=tmpdir)
    finally:
        # Clean up our temporary working directory
        if tmpdir:
            shutil.rmtree(tmpdir, ignore_errors=True)


DATA = b\"\"\"
{zipfile}
\"\"\"


if __name__ == "__main__":
    main()
""".lstrip()

    # Get all of the files we want to add to the zip file
    print("[generate.installer] Collect all the files that should be zipped")
    all_files = []
    for root, dirs, files in os.walk(os.path.join(paths.PROJECT_ROOT, "pip")):
        for pyfile in files:
            if os.path.splitext(pyfile)[1] in {".py", ".pem", ".cfg", ".exe"}:
                path = os.path.join(root, pyfile)
                all_files.append(
                    "/".join(
                        path.split("/")[len(paths.PROJECT_ROOT.split("/")):]
                    )
                )

    tmpdir = tempfile.mkdtemp()
    try:
        # Get a temporary path to use as staging for the pip zip
        zpth = os.path.join(tmpdir, "pip.zip")

        # Write the pip files to the zip archive
        print("[generate.installer] Generate the bundled zip of pip")
        with zipfile.ZipFile(zpth, "w", compression=zipfile.ZIP_DEFLATED) as z:
            for filename in all_files:
                z.write(os.path.join(paths.PROJECT_ROOT, filename), filename)

        # Get the binary data that compromises our zip file
        with open(zpth, "rb") as fp:
            data = fp.read()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    # Write out the wrapper script that will take the place of the zip script
    # The reason we need to do this instead of just directly executing the
    # zip script is that while Python will happily execute a zip script if
    # passed it on the file system, it will not however allow this to work if
    # passed it via stdin. This means that this wrapper script is required to
    # make ``curl https://...../get-pip.py | python`` continue to work.
    print(
        "[generate.installer] Write the wrapper script with the bundled zip "
        "file"
    )

    zipdata = base64.b85encode(data).decode("utf8")
    chunked = []

    for i in range(0, len(zipdata), 79):
        chunked.append(zipdata[i:i + 79])

    with open(installer_path, "w") as fp:
        fp.write(WRAPPER_SCRIPT.format(zipfile="\n".join(chunked)))

    # Ensure the permissions on the newly created file
    oldmode = os.stat(installer_path).st_mode & 0o7777
    newmode = (oldmode | 0o555) & 0o7777
    os.chmod(installer_path, newmode)

    print("[generate.installer] Generated installer")

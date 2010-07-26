#!/usr/bin/env python

import os
import sys
import zipfile

try:
    import zlib
    compression = zipfile.ZIP_DEFLATED
except:
    compression = zipfile.ZIP_STORED

def main():
    file_name = 'pip.zip'
    zf = zipfile.PyZipFile(file_name, mode='w', compression=compression)
    try:
        zf.debug = 4
        for package in ['pip', '__main__.py']:
            zf.writepy(package)
    finally:
        zf.close()
    pip_zip = open(file_name, 'r')
    content = pip_zip.read()
    pip_zip.close()

    pip_zip = open(file_name, 'w')
    pip_zip.write("#!/usr/bin/env python\n"+content)
    pip_zip.close()

    if hasattr(os, 'chmod'):
        oldmode = os.stat(file_name).st_mode & 07777
        newmode = (oldmode | 0555) & 07777
        os.chmod(file_name, newmode)
        print 'Made resulting file executable. Use it as `./%s`.' % file_name

if __name__ == '__main__':
    main()


from pip.commands.zip import ZipCommand


class UnzipCommand(ZipCommand):
    name = 'unzip'
    summary = 'unzip individual packages'

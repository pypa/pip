
from pip.basecommand import Command

class PluginCommand(Command):
    """
    Do Plugin stuff
    """
    name = 'plugin'
    usage = """
      %prog [options] """
    summary = 'Do Plugin stuff'

    def run(self, options, args):
        pass

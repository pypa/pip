import os
import copy
from pip import main
from pip import cmdoptions
from pip.basecommand import Command
from pip.commands import InstallCommand
from pip.commands import commands

class FakeCommand(Command):
    name = 'fake'
    summary = name
    def main(self, args):
        return self.parse_args(args)

class TestCommandParsing(object):

    def setup(self):
        self.environ_before = os.environ.copy()
        commands[FakeCommand.name] = FakeCommand

    def teardown(self):
        os.environ = self.environ_before
        commands.pop(FakeCommand.name)

    def different_than_default(self, option):
        """
        Generate something different than the option default
        Returns a tuple containing:
           - the value to test against getattr(options, option.dest)
           - the args to achieve it , e.g ['--log', '/path']
        """
        NO_DEFAULT = (option.default == ('NO', 'DEFAULT'))
        long_opt = option._long_opts[0]

        if option.type == 'choice':
            dest = option.default[:]
            dest.append(option.choices[0])
            if dest == option.default:
                assert False, "The test is not altering the default"
            args = []
            for d in dest:
                args.extend([long_opt, d])
        elif option.type in ['str', 'string']:
            if NO_DEFAULT:
                dest = 'CHANGED'
            else:
                dest = option.default + 'CHANGED'
            args = [long_opt, dest]
        elif option.action == 'count':
            dest = option.default + 1
            args = [long_opt]
        elif option.type == 'float':
            dest = option.default + 100
            args = [long_opt, str(dest)]
        elif option.action == 'store_true':
            dest = not option.default
            args = [long_opt]
        elif option.default == ('NO', 'DEFAULT'):
             dest = 'CHANGED'
             args = [long_opt, dest]

        return dest, args

    def test_general_options_dont_have_duplicated_defaults(self):
        """
        Confirm that 'append' options don't end up with duplicated defaults.
        """
        # It's possible for our general options to be used twice during command
        # initialization, e.g. `--exists-action` option will be used twice in
        # this case: "pip --exists-action s install somepkg". And if they carry
        # state (like append options with [] defaults) then this can be
        # trouble. We need to confirm this is not happening.
        options, args = main(['--exists-action', 's', 'fake'])
        assert options.exists_action == ['s'] # not ['s','s']

    def test_cli_override_general_options(self):
        """
        Test overriding default values for general options using the cli
        (not referring to config or environment overrides)
        """
        # the reason to specifically test general options is due to the
        # extra parsing they receive, and the bugs we've had
        for option_maker in cmdoptions.general_group['options']:
            option = option_maker.make()
            if option.dest in ['help', 'version']:
                continue
            expected_dest, opt_args = self.different_than_default(option)

            # we're going to check with the args before and after the subcommand
            # our parser allows general options to live after the subcommand
            for args in (opt_args + ['fake'], ['fake'] + opt_args):
                options, args_ = main(args)
                msg = "%s != %s with args %s" %(
                    getattr(options, option.dest),
                    expected_dest,
                    args
                    )
                assert getattr(options, option.dest) == expected_dest, msg


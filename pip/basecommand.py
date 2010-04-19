"""Base Command class, and related routines"""

import sys
import os
import socket
import urllib2
import urllib
from cStringIO import StringIO
import traceback
import time
from pip.log import logger
from pip.baseparser import parser, ConfigOptionParser, UpdatingDefaultsHelpFormatter
from pip.exceptions import BadCommand, InstallationError, UninstallationError
from pip.venv import restart_in_venv

__all__ = ['command_dict', 'Command', 'load_all_commands',
           'load_command', 'command_names']

command_dict = {}

class Command(object):
    name = None
    usage = None
    hidden = False
    def __init__(self):
        assert self.name
        self.parser = ConfigOptionParser(
            usage=self.usage,
            prog='%s %s' % (sys.argv[0], self.name),
            version=parser.version,
            formatter=UpdatingDefaultsHelpFormatter(),
            name=self.name)
        for option in parser.option_list:
            if not option.dest or option.dest == 'help':
                # -h, --version, etc
                continue
            self.parser.add_option(option)
        command_dict[self.name] = self

    def merge_options(self, initial_options, options):
        # Make sure we have all global options carried over
        for attr in ['log', 'venv', 'proxy', 'venv_base', 'require_venv',
                     'respect_venv', 'log_explicit_levels', 'log_file',
                     'timeout', 'default_vcs', 'skip_requirements_regex']:
            setattr(options, attr, getattr(initial_options, attr) or getattr(options, attr))
        options.quiet += initial_options.quiet
        options.verbose += initial_options.verbose

    def setup_logging(self):
        pass
        
    def main(self, complete_args, args, initial_options):
        options, args = self.parser.parse_args(args)
        self.merge_options(initial_options, options)

        level = 1 # Notify
        level += options.verbose
        level -= options.quiet
        level = logger.level_for_integer(4-level)
        complete_log = []
        logger.consumers.extend(
            [(level, sys.stdout),
             (logger.DEBUG, complete_log.append)])
        if options.log_explicit_levels:
            logger.explicit_levels = True

        self.setup_logging()
            
        if options.require_venv and not options.venv:
            # If a venv is required check if it can really be found
            if not os.environ.get('VIRTUAL_ENV'):
                logger.fatal('Could not find an activated virtualenv (required).')
                sys.exit(3)
            # Automatically install in currently activated venv if required
            options.respect_venv = True

        if args and args[-1] == '___VENV_RESTART___':
            ## FIXME: We don't do anything this this value yet:
            venv_location = args[-2]
            args = args[:-2]
            options.venv = None
        else:
            # If given the option to respect the activated environment
            # check if no venv is given as a command line parameter
            if options.respect_venv and os.environ.get('VIRTUAL_ENV'):
                if options.venv and os.path.exists(options.venv):
                    # Make sure command line venv and environmental are the same
                    if (os.path.realpath(os.path.expanduser(options.venv)) !=
                            os.path.realpath(os.environ.get('VIRTUAL_ENV'))):
                        logger.fatal("Given virtualenv (%s) doesn't match "
                                     "currently activated virtualenv (%s)."
                                     % (options.venv, os.environ.get('VIRTUAL_ENV')))
                        sys.exit(3)
                else:
                    options.venv = os.environ.get('VIRTUAL_ENV')
                    logger.info('Using already activated environment %s' % options.venv)
        if options.venv:
            logger.info('Running in environment %s' % options.venv)
            site_packages=False
            if options.site_packages:
                site_packages=True
            restart_in_venv(options.venv, options.venv_base, site_packages,
                            complete_args)
            # restart_in_venv should actually never return, but for clarity...
            return

        ## FIXME: not sure if this sure come before or after venv restart
        if options.log:
            log_fp = open_logfile(options.log, 'a')
            logger.consumers.append((logger.DEBUG, log_fp))
        else:
            log_fp = None

        socket.setdefaulttimeout(options.timeout or None)

        setup_proxy_handler(options.proxy)

        exit = 0
        try:
            self.run(options, args)
        except (InstallationError, UninstallationError), e:
            logger.fatal(str(e))
            logger.info('Exception information:\n%s' % format_exc())
            exit = 1
        except BadCommand, e:
            logger.fatal(str(e))
            logger.info('Exception information:\n%s' % format_exc())
            exit = 1
        except:
            logger.fatal('Exception:\n%s' % format_exc())
            exit = 2

        if log_fp is not None:
            log_fp.close()
        if exit:
            log_fn = options.log_file
            text = '\n'.join(complete_log)
            logger.fatal('Storing complete log in %s' % log_fn)
            log_fp = open_logfile(log_fn, 'w')
            log_fp.write(text)
            log_fp.close()
        return exit

## FIXME: should get moved somewhere else:
def setup_proxy_handler(proxystr=''):
    """Set the proxy handler given the option passed on the command
    line.  If an empty string is passed it looks at the HTTP_PROXY
    environment variable.  """
    proxy = get_proxy(proxystr)
    if proxy:
        proxy_support = urllib2.ProxyHandler({"http": proxy, "ftp": proxy})
        opener = urllib2.build_opener(proxy_support, urllib2.CacheFTPHandler)
        urllib2.install_opener(opener)

def get_proxy(proxystr=''):
    """Get the proxy given the option passed on the command line.  If an
    empty string is passed it looks at the HTTP_PROXY environment
    variable."""
    if not proxystr:
        proxystr = os.environ.get('HTTP_PROXY', '')
    if proxystr:
        if '@' in proxystr:
            user_password, server_port = proxystr.split('@', 1)
            if ':' in user_password:
                user, password = user_password.split(':', 1)
            else:
                user = user_password
                import getpass
                prompt = 'Password for %s@%s: ' % (user, server_port)
                password = urllib.quote(getpass.getpass(prompt))
            return '%s:%s@%s' % (user, password, server_port)
        else:
            return proxystr
    else:
        return None

def format_exc(exc_info=None):
    if exc_info is None:
        exc_info = sys.exc_info()
    out = StringIO()
    traceback.print_exception(*exc_info, **dict(file=out))
    return out.getvalue()

def open_logfile(filename, mode='a'):
    """Open the named log file in append mode.

    If the file already exists, a separator will also be printed to
    the file to separate past activity from current activity.
    """
    filename = os.path.expanduser(filename)
    filename = os.path.abspath(filename)
    dirname = os.path.dirname(filename)
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    exists = os.path.exists(filename)
    log_fp = open(filename, mode)
    if exists:
        print >> log_fp, '-'*60
        print >> log_fp, '%s run on %s' % (sys.argv[0], time.strftime('%c'))
    return log_fp

def load_command(name):
    full_name = 'pip.commands.%s' % name
    if full_name in sys.modules:
        return
    try:
        __import__(full_name)
    except ImportError:
        pass

def load_all_commands():
    for name in command_names():
        load_command(name)

def command_names():
    dir = os.path.join(os.path.dirname(__file__), 'commands')
    names = []
    for name in os.listdir(dir):
        if name.endswith('.py') and os.path.isfile(os.path.join(dir, name)):
            names.append(os.path.splitext(name)[0])
    return names

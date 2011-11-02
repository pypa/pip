import pip
import pkg_resources
import re
import sys
from pip.log import logger
from pip.req import InstallRequirement
from pip.util import get_installed_distributions


class FreezeData(list):
    """
    An listish collection for holding and handling data for building a
    requirement file or similar data structure.
    """
    def __init__(self, local_only=False, find_links=[], find_tags=False, write_on_load=True, handle=sys.stderr, logger=logger):
        self.installations = {}
        self.logger = logger
        self.local_only = local_only
        self.find_tags = find_tags
        self.write_on_load = write_on_load
        self.handle = handle
        self.find_links = find_links

    @classmethod
    def load_all(cls, local_only=False, find_links=[], requirement=None, find_tags=False,
                 skip_requirements_regex=None, default_vcs=None,
                 write_on_load=True, handle=sys.stderr, logger=logger):
        """
        A factory that loads all requirment information for the
        current environment.
        """
        data = cls(local_only, find_links, find_tags, write_on_load, handle, logger)
        data.load("-f %s\n" %link for link in data.dependency_links)
        data.load_installed(requirement, skip_requirements_regex, default_vcs)
        return data

    def load_installed(self, requirement=None, skip_requirements_regex=None, default_vcs=None):
        """
        Load data for all installed packages using a requirements file
        to provide hints.
        """
        installations = self._installed_distributions()
        if requirement:
            self.load(self.requirement_lines(requirement, skip_requirements_regex, default_vcs))\
                .load('## The following requirements were added by pip --freeze:\n')

        for installation in sorted(installations.values(), key=lambda x: x.name):
            self.load(str(installation))

        return self

    def load(self, data):
        write = self.write_on_load and self.handle
        if isinstance(data, basestring):
            self.append(data)
            if write: self.handle.write(data) 
        else:
            data = list(data)
            self.extend(data)
            if write: [self.handle.write(datum) for datum in data] 
        return self

    flag_keys = {'-f':'find_links',
                 '-i':'indexes',
                 '-e':'editable'}
    
    FLAG = re.compile(r'^(?P<flag>\-e|\-f|\-i)\s+(?P<url>.*)$' )

    @property
    def as_dict(self):
        if sys.version_info.major >= 2 and sys.version_info.minor >= 7:
            from collections import OrderedDict as dict_class
        else:
            dict_class = dict

        outdata = dict_class(find_links=[],
                             editable=[],
                             indexes=[],
                             requirements=dict_class())

        for line in sorted(self):
            if line.startswith('#'):
                continue
            
            elif line.startswith('-'):
                match = self.FLAG.match(line)
                data = match.groupdict()
                if match:
                    key = self.flag_keys[data['flag']]
                    outdata[key].append(data['url'])

            elif not line.startswith('-'):
                pkg, version = line.split('==')
                outdata['requirements'][pkg] = version.strip()

        return outdata

    @property
    def text(self):
        return [self.handle.write(line) for line in self]

    @property
    def dependency_link_generator(self):
        for dist in pkg_resources.working_set:
            if dist.has_metadata('dependency_links.txt'):
                for link in dist.get_metadata_lines('dependency_links.txt'):
                    yield link
                    
        for link in self.find_links:
            if '#egg=' in link:
                yield link

    @property
    def dependency_links(self):
        memo = getattr(self, '_dependency_link_memo', None)
        if memo is None:
            memo = self._dependency_link_memo = list(self.dependency_link_generator)
        return memo

    def _installed_distributions(self):
        installations = {}
        for dist in get_installed_distributions(local_only=self.local_only):
            try:
                req = pip.FrozenRequirement.from_dist(dist, self.dependency_links, find_tags=self.find_tags)
            except :
                import pdb, sys; pdb.post_mortem(sys.exc_info()[2])
                raise
            installations[req.name] = req
        return installations
                
    def write_requirement(self, requirement, skip_regex=None, default_vcs='git'):
        if skip_regex:
            skip_match = re.compile(skip_regex)
        req_f = open(requirement)
        for line in req_f:
            if not line.strip() or line.strip().startswith('#'):
                yield line
                continue
            if skip_match and skip_match.search(line):
                yield line
                continue
            elif line.startswith('-e') or line.startswith('--editable'):
                if line.startswith('-e'):
                    line = line[2:].strip()
                else:
                    line = line[len('--editable'):].strip().lstrip('=')
                line_req = InstallRequirement.from_editable(line, default_vcs=default_vcs)
            elif (line.startswith('-r') or line.startswith('--requirement')
                  or line.startswith('-Z') or line.startswith('--always-unzip')
                  or line.startswith('-f') or line.startswith('-i')
                  or line.startswith('--extra-index-url')):
                yield line
                continue
            else:
                line_req = InstallRequirement.from_line(line)
            if not line_req.name:
                self.logger.notify("Skipping line because it's not clear what it would install: %s"
                              % line.strip())
                self.logger.notify("  (add #egg=PackageName to the URL to avoid this warning)")
                continue
            if line_req.name not in self.installations:
                self.logger.warn("Requirement file contains %s, but that package is not installed"
                            % line.strip())
                continue
            yield str(self.installations[line_req.name])
            del self.installations[line_req.name]

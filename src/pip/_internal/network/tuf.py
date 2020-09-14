""" TUF (TheUpdateFramework) integration
"""

import hashlib
import logging
import os.path

from pip._vendor.six.moves.urllib import parse as urllib_parse

# TODO vendor tuf
import tuf.client.updater
from tuf.exceptions import (
    RepositoryError,
)
import tuf.settings


logger = logging.getLogger(__name__)


# TUF Updater abstraction for a specific Warehouse instance (index URL)
class Updater:
    # throws RepositoryError, ?
    def __init__(self, index_url, metadata_dir, cache_dir):
        # Construct unique directory name based on the url
        # TODO make sure this is robust
        dir_name = hashlib.sha224(index_url.encode('utf-8')).hexdigest()
        
        # we expect metadata and index files to be hosted on same netloc
        split_url = urllib_parse.urlsplit(index_url)
        base_url = urllib_parse.urlunsplit([split_url.scheme, split_url.netloc, '', '', ''])
        targets_path = split_url.path.lstrip('/')

        # Store two separate mirror configs to workaround https://github.com/theupdateframework/tuf/issues/1143
        # TODO: metadata_path should not be hard coded but solution is not decided yet
        self._index_mirrors = {
            base_url: {
                'url_prefix': base_url,
                'metadata_path': 'tuf/',
                'targets_path': targets_path,
                'confined_target_dirs': ['']
            }
        }
        self._distribution_mirrors = {
            base_url: {
                'url_prefix': base_url,
                'metadata_path': 'tuf/',
                'targets_path': 'None', # TODO: Actual None does not work with current tuf 
                'confined_target_dirs': []
            }
        }

        self._updater = tuf.client.updater.Updater(dir_name, self._index_mirrors)
        self._refreshed = False

        # TODO think cache issue through:
        #  * do we need a cache, is it actually useful?
        #  * what if cache_dir is None?
        self._cache_dir = cache_dir


    def __str__(self):
        return str(self._updater)


    # Make sure we have refreshed metadata exactly once (we
    # want all downloads to be done from a consistent repository)
    # Raises NoWorkingMirrorError, ?
    def _ensure_fresh_metadata(self):
        if not self._refreshed:
            self._updater.refresh()
            self._refreshed = True


    # Ensure give mirror is in updater mirror config
    def _ensure_distribution_mirror_config(self, mirror_url):
        # metadata/index mirror config is known from the start, but 
        # the distribution mirror is only known after the index
        # files are read: make sure it's configured

        # TODO: split mirror_url into prefix and targets_path ?
        # This would allow using confined_target_dirs to prevent
        # index file requests being made to this mirror
        if mirror_url not in self._distribution_mirrors:
            self._distribution_mirrors[mirror_url] = {
                'url_prefix': mirror_url,
                'metadata_path': 'None', # TODO: Actual None does not work with current tuf 
                'targets_path': '',
                'confined_target_dirs': ['']
            }


    # split a distribution url into base path and target name:
    # "https://files.pythonhosted.org/packages/8f/1f/74aa91b56dea5847b62e11ce6737db82c6446561bddc20ca80fa5df025cc/Django-1.1.3.tar.gz#sha256=0e5034cf8046ba77c62e95a45d776d2c59998b26f181ceaf5cec516115e3f85a"
    #    ->
    # ("https://files.pythonhosted.org/packages/", "8f/1f/74aa91b56dea5847b62e11ce6737db82c6446561bddc20ca80fa5df025cc/Django-1.1.3.tar.gz")
    def _split_distribution_url(self, link):
        # TODO replace the hack with a proper split based on
        # knowledge of the hash
        base_url = urllib_parse.urlunsplit([link.scheme, link.netloc, "/packages/", "", ""])
        target = link.path[len("/packages/"):]
        return base_url, target


    # Download project index file, return file name
    # project name is e.g. 'django'. From pypi this will download
    # "https://pypi.org/simple/django"
    # Raises NoWorkingMirrorError, ?
    def download_index(self, project_name):
        self._ensure_fresh_metadata()

        self._updater.mirrors = self._index_mirrors

        # TODO warehouse setup for hashed index files is still undecided: this assumes /simple/{PROJECT}/{HASH}.index.html
        target_name = project_name + "/index.html"
        target = self._updater.get_one_valid_targetinfo(target_name)
        if self._updater.updated_targets([target], self._cache_dir):
            self._updater.download_target(target, self._cache_dir)

        # TODO possibly we want to return contents of the file instead?
        return os.path.join(self._cache_dir, target_name)


    # Download a distribution file
    # Requires a link with url and comes_from
    #   url is e.g. https://files.pythonhosted.org/packages/8f/1f/74aa91b56dea5847b62e11ce6737db82c6446561bddc20ca80fa5df025cc/Django-1.1.3.tar.gz#sha256=0e5034cf8046ba77c62e95a45d776d2c59998b26f181ceaf5cec516115e3f85a
    #   comes_from is e.g. "https://pypi.org/simple/django"
    # Raises NoWorkingMirrorError, ?
    def download_distribution(self, link):
        # TODO double check that comes_from matches our index_url

        self._ensure_fresh_metadata()

        base_url, target_name = self._split_distribution_url(link)
        self._ensure_distribution_mirror_config(base_url)
        self._updater.mirrors = self._distribution_mirrors

        logger.debug("Getting TUF target_info for " + target_name)
        target = self._updater.get_one_valid_targetinfo(target_name)
        
        # TODO decide cache dir strategy. Currently the whole
        # directory structure is created in _cache_dir. Also 'None' cache dir breaks everything
        if self._updater.updated_targets([target], self._cache_dir):
            self._updater.download_target(target, self._cache_dir, prefix_filename_with_hash=False)
        return os.path.join(self._cache_dir, target_name)



# Return a dictionary of index_url:Updater
# The dict will contain updaters for every index_url that we have local metadata for
# TODO return value should maybe be a "TUFSession" object -- it could provide some extra
# functionality like updater lookup based on distribution download Link (currently
# implemented in prepare.py:get_http_url()) or lookup that at least canonicalizes the URL
def initialize_updaters(index_urls, metadata_dir, cache_dir):
    if not os.path.isdir(metadata_dir):
        # TODO should create this path or no?
        raise NotADirectoryError(metadata_dir) # TODO not in py2

    # global TUF settings
    tuf.settings.repositories_directory = metadata_dir
    tuf.log.set_log_level(logging.INFO)

    # Initialize updaters for index_urls with local metadata
    updaters = {}
    for index_url in index_urls:
        # TODO: should canonicalize index_url: at least the last slash
        try:
            updaters[index_url] = Updater(index_url, metadata_dir, cache_dir)
        except RepositoryError as e:
            # No TUF Metadata was found for this index_url
            # TODO: must check for actual metadata file existence
            # otherwise RepositoryError means "no local metadata"
            # and "something is wrong"
            logger.info("Failed to find TUF repo for '%s': %s", index_url, e)
    
    return updaters

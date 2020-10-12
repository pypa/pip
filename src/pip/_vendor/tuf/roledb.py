#!/usr/bin/env python

# Copyright 2012 - 2017, New York University and the TUF contributors
# SPDX-License-Identifier: MIT OR Apache-2.0

"""
<Program Name>
  roledb.py

<Author>
  Vladimir Diaz <vladimir.v.diaz@gmail.com>

<Started>
  March 21, 2012.  Based on a previous version of this module by Geremy Condra.

<Copyright>
  See LICENSE-MIT OR LICENSE for licensing information.

<Purpose>
  Represent a collection of roles and their organization.  The caller may
  create a collection of roles from those found in the 'root.json' metadata
  file by calling 'create_roledb_from_root_metadata()', or individually by
  adding roles with 'add_role()'.  There are many supplemental functions
  included here that yield useful information about the roles contained in the
  database, such as extracting all the parent rolenames for a specified
  rolename, deleting all the delegated roles, retrieving role paths, etc.  The
  Update Framework process maintains a role database for each repository.

  The role database is a dictionary conformant to
  'tuf.formats.ROLEDICT_SCHEMA' and has the form:

  {'repository_name': {
      'rolename': {'keyids': ['34345df32093bd12...'],
          'threshold': 1
          'signatures': ['abcd3452...'],
          'paths': ['role.json'],
          'path_hash_prefixes': ['ab34df13'],
          'delegations': {'keys': {}, 'roles': {}}}

  The 'name', 'paths', 'path_hash_prefixes', and 'delegations' dict keys are
  optional.
"""

# Help with Python 3 compatibility, where the print statement is a function, an
# implicit relative import is invalid, and the '/' operator performs true
# division.  Example:  print 'hello world' raises a 'SyntaxError' exception.
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging
import copy

class _Dummy(object):
  pass
tuf = _Dummy()
from pip._vendor.tuf import exceptions as _tuf_exceptions
tuf.exceptions = _tuf_exceptions
from pip._vendor.tuf import formats as _tuf_formats
tuf.formats = _tuf_formats

securesystemslib = _Dummy()
from pip._vendor.securesystemslib import formats as _securesystemslib_formats
securesystemslib.formats = _securesystemslib_formats
from pip._vendor.securesystemslib import exceptions as _securesystemslib_exceptions
securesystemslib.exceptions = _securesystemslib_exceptions
from pip._vendor import six

# See 'tuf.log' to learn how logging is handled in TUF.
logger = logging.getLogger(__name__)

# The role database.
_roledb_dict = {}
_roledb_dict['default'] = {}

# A dictionary (where the keys are repository names) containing a set of roles
# that have been modified (e.g., via update_roleinfo()) and should be written
# to disk.
_dirty_roles = {}
_dirty_roles['default'] = set()


TOP_LEVEL_ROLES = ['root', 'targets', 'snapshot', 'timestamp']


def create_roledb_from_root_metadata(root_metadata, repository_name='default'):
  """
  <Purpose>
    Create a role database containing all of the unique roles found in
    'root_metadata'.

  <Arguments>
    root_metadata:
      A dictionary conformant to 'tuf.formats.ROOT_SCHEMA'.  The
      roles found in the 'roles' field of 'root_metadata' is needed by this
      function.

    repository_name:
      The name of the repository to store 'root_metadata'.  If not supplied,
      'rolename' is added to the 'default' repository.

  <Exceptions>
    securesystemslib.exceptions.FormatError, if 'root_metadata' does not have
    the correct object format.

    securesystemslib.exceptions.Error, if one of the roles found in
    'root_metadata' contains an invalid delegation (i.e., a nonexistent parent
    role).

  <Side Effects>
    Calls add_role().  The old role database for 'repository_name' is replaced.

  <Returns>
    None.
  """

  # Does 'root_metadata' have the correct object format?
  # This check will ensure 'root_metadata' has the appropriate number of objects
  # and object types, and that all dict keys are properly named.
  # Raises securesystemslib.exceptions.FormatError.
  tuf.formats.ROOT_SCHEMA.check_match(root_metadata)

  # Is 'repository_name' formatted correctly?
  securesystemslib.formats.NAME_SCHEMA.check_match(repository_name)

  global _roledb_dict
  global _dirty_roles

  # Clear the role database.
  if repository_name in _roledb_dict:
    _roledb_dict[repository_name].clear()

  # Ensure _roledb_dict and _dirty_roles contains an entry for
  # 'repository_name' so that adding the newly created roleinfo succeeds.
  _roledb_dict[repository_name] = {}
  _dirty_roles[repository_name] = set()

  # Do not modify the contents of the 'root_metadata' argument.
  root_metadata = copy.deepcopy(root_metadata)

  # Iterate the roles found in 'root_metadata' and add them to '_roledb_dict'.
  # Duplicates are avoided.
  for rolename, roleinfo in six.iteritems(root_metadata['roles']):
    if rolename == 'root':
      roleinfo['version'] = root_metadata['version']
      roleinfo['expires'] = root_metadata['expires']
      roleinfo['previous_keyids'] = roleinfo['keyids']
      roleinfo['previous_threshold'] = roleinfo['threshold']

    roleinfo['signatures'] = []
    roleinfo['signing_keyids'] = []
    roleinfo['partial_loaded'] = False

    if rolename.startswith('targets'):
      roleinfo['paths'] = {}
      roleinfo['delegations'] = {'keys': {}, 'roles': []}

    add_role(rolename, roleinfo, repository_name)





def create_roledb(repository_name):
  """
  <Purspose>
    Create a roledb for the repository named 'repository_name'.  This function
    is intended for creation of a non-default roledb.

  <Arguments>
    repository_name:
      The name of the repository to create. An empty roledb is created, and
      roles may be added via add_role(rolename, roleinfo, repository_name) or
      create_roledb_from_root_metadata(root_metadata, repository_name).

  <Exceptions>
    securesystemslib.exceptions.FormatError, if 'repository_name' is improperly
    formatted.

    securesystemslib.exceptions.InvalidNameError, if 'repository_name' already
    exists in the roledb.

  <Side Effects>
    None.

  <Returns>
    None.
  """

  # Is 'repository_name' properly formatted?  If not, raise
  # 'securesystemslib.exceptions.FormatError'.
  securesystemslib.formats.NAME_SCHEMA.check_match(repository_name)

  global _roledb_dict
  global _dirty_roles

  if repository_name in _roledb_dict or repository_name in _dirty_roles:
    raise securesystemslib.exceptions.InvalidNameError('Repository name'
      ' already exists: ' + repr(repository_name))

  _roledb_dict[repository_name] = {}
  _dirty_roles[repository_name] = set()





def remove_roledb(repository_name):
  """
  <Purspose>
    Remove the roledb belonging to 'repository_name'.

  <Arguments>
    repository_name:
      The name of the repository to remove.  'repository_name' cannot be
      'default' because the default repository is expected to always exist.

  <Exceptions>
    securesystemslib.exceptions.FormatError, if 'repository_name' is improperly
    formatted.

    securesystemslib.exceptions.InvalidNameError, if 'repository_name' is the
    'default' repository name.  The 'default' repository name should always
    exist.

  <Side Effects>
    None.

  <Returns>
    None.
  """

  # Is 'repository_name' properly formatted?  If not, raise
  # 'securesystemslib.exceptions.FormatError'.
  securesystemslib.formats.NAME_SCHEMA.check_match(repository_name)

  global _roledb_dict
  global _dirty_roles

  if repository_name not in _roledb_dict or repository_name not in _dirty_roles:
    logger.warning('Repository name does not exist:'
      ' ' + repr(repository_name))
    return

  if repository_name == 'default':
    raise securesystemslib.exceptions.InvalidNameError('Cannot remove the'
      ' default repository: ' + repr(repository_name))

  del _roledb_dict[repository_name]
  del _dirty_roles[repository_name]



def add_role(rolename, roleinfo, repository_name='default'):
  """
  <Purpose>
    Add to the role database the 'roleinfo' associated with 'rolename'.

  <Arguments>
    rolename:
      An object representing the role's name, conformant to 'ROLENAME_SCHEMA'
      (e.g., 'root', 'snapshot', 'timestamp').

    roleinfo:
      An object representing the role associated with 'rolename', conformant to
      ROLEDB_SCHEMA.  'roleinfo' has the form:
      {'keyids': ['34345df32093bd12...'],
       'threshold': 1,
       'signatures': ['ab23dfc32']
       'paths': ['path/to/target1', 'path/to/target2', ...],
       'path_hash_prefixes': ['a324fcd...', ...],
       'delegations': {'keys': }

      The 'paths', 'path_hash_prefixes', and 'delegations' dict keys are
      optional.

      The 'target' role has an additional 'paths' key.  Its value is a list of
      strings representing the path of the target file(s).

    repository_name:
      The name of the repository to store 'rolename'.  If not supplied,
      'rolename' is added to the 'default' repository.

  <Exceptions>
    securesystemslib.exceptions.FormatError, if 'rolename' or 'roleinfo' does
    not have the correct object format.

    securesystemslib.exceptions.RoleAlreadyExistsError, if 'rolename' has
    already been added.

    securesystemslib.exceptions.InvalidNameError, if 'rolename' is improperly
    formatted, or 'repository_name' does not exist.

  <Side Effects>
    The role database is modified.

  <Returns>
    None.
  """

  # Does 'rolename' have the correct object format?
  # This check will ensure 'rolename' has the appropriate number of objects
  # and object types, and that all dict keys are properly named.
  tuf.formats.ROLENAME_SCHEMA.check_match(rolename)

  # Does 'roleinfo' have the correct object format?
  tuf.formats.ROLEDB_SCHEMA.check_match(roleinfo)

  # Is 'repository_name' correctly formatted?
  securesystemslib.formats.NAME_SCHEMA.check_match(repository_name)

  global _roledb_dict

  # Raises securesystemslib.exceptions.InvalidNameError.
  _validate_rolename(rolename)

  if repository_name not in _roledb_dict:
    raise securesystemslib.exceptions.InvalidNameError('Repository name does not exist: ' + repository_name)

  if rolename in _roledb_dict[repository_name]:
    raise tuf.exceptions.RoleAlreadyExistsError('Role already exists: ' + rolename)

  _roledb_dict[repository_name][rolename] = copy.deepcopy(roleinfo)





def update_roleinfo(rolename, roleinfo, mark_role_as_dirty=True, repository_name='default'):
  """
  <Purpose>
    Modify 'rolename's _roledb_dict entry to include the new 'roleinfo'.
    'rolename' is also added to the _dirty_roles set.  Roles added to
    '_dirty_roles' are marked as modified and can be used by the repository
    tools to determine which roles need to be written to disk.

  <Arguments>
    rolename:
      An object representing the role's name, conformant to 'ROLENAME_SCHEMA'
      (e.g., 'root', 'snapshot', 'timestamp').

    roleinfo:
      An object representing the role associated with 'rolename', conformant to
      ROLEDB_SCHEMA.  'roleinfo' has the form:
      {'name': 'role_name',
       'keyids': ['34345df32093bd12...'],
       'threshold': 1,
       'paths': ['path/to/target1', 'path/to/target2', ...],
       'path_hash_prefixes': ['a324fcd...', ...]}

      The 'name', 'paths', and 'path_hash_prefixes' dict keys are optional.

      The 'target' role has an additional 'paths' key.  Its value is a list of
      strings representing the path of the target file(s).

    mark_role_as_dirty:
      A boolean indicating whether the updated 'roleinfo' for 'rolename' should
      be marked as dirty.  The caller might not want to mark 'rolename' as
      dirty if it is loading metadata from disk and only wants to populate
      roledb.py.  Likewise, add_role() would support a similar boolean to allow
      the repository tools to successfully load roles via load_repository()
      without needing to mark these roles as dirty (default behavior).

    repository_name:
      The name of the repository to update the roleinfo of 'rolename'.  If not
      supplied, the 'default' repository is searched.

  <Exceptions>
    securesystemslib.exceptions.FormatError, if 'rolename' or 'roleinfo' does
    not have the correct object format.

    tuf.exceptions.UnknownRoleError, if 'rolename' cannot be found
    in the role database.

    securesystemslib.exceptions.InvalidNameError, if 'rolename' is improperly
    formatted, or 'repository_name' does not exist in the role database.

  <Side Effects>
    The role database is modified.

  <Returns>
    None.
  """

  # Does the arguments have the correct object format?
  # This check will ensure arguments have the appropriate number of objects
  # and object types, and that all dict keys are properly named.
  tuf.formats.ROLENAME_SCHEMA.check_match(rolename)
  securesystemslib.formats.BOOLEAN_SCHEMA.check_match(mark_role_as_dirty)
  securesystemslib.formats.NAME_SCHEMA.check_match(repository_name)

  # Does 'roleinfo' have the correct object format?
  tuf.formats.ROLEDB_SCHEMA.check_match(roleinfo)

  # Raises securesystemslib.exceptions.InvalidNameError.
  _validate_rolename(rolename)

  global _roledb_dict
  global _dirty_roles

  if repository_name not in _roledb_dict or repository_name not in _dirty_roles:
    raise securesystemslib.exceptions.InvalidNameError('Repository name does not' ' exist: ' +
      repository_name)

  if rolename not in _roledb_dict[repository_name]:
    raise tuf.exceptions.UnknownRoleError('Role does not exist: ' + rolename)

  # Update the global _roledb_dict and _dirty_roles structures so that
  # the latest 'roleinfo' is available to other modules, and the repository
  # tools know which roles should be saved to disk.
  _roledb_dict[repository_name][rolename] = copy.deepcopy(roleinfo)

  if mark_role_as_dirty:
    _dirty_roles[repository_name].add(rolename)





def get_dirty_roles(repository_name='default'):
  """
  <Purpose>
    A function that returns a list of the roles that have been modified.  Tools
    that write metadata to disk can use the list returned to determine which
    roles should be written.

  <Arguments>
    repository_name:
      The name of the repository to get the dirty roles.  If not supplied, the
      'default' repository is searched.

  <Exceptions>
    securesystemslib.exceptions.FormatError, if 'repository_name' is improperly
    formatted.

    securesystemslib.exceptions.InvalidNameError, if 'repository_name' does not
    exist in the role database.

  <Side Effects>
    None.

  <Returns>
    A sorted list of the roles that have been modified.
  """

  # Does 'repository_name' have the correct format?  Raise
  # 'securesystemslib.exceptions.FormatError' if not.
  securesystemslib.formats.NAME_SCHEMA.check_match(repository_name)

  global _roledb_dict
  global _dirty_roles

  if repository_name not in _roledb_dict or repository_name not in _dirty_roles:
    raise securesystemslib.exceptions.InvalidNameError('Repository name does'
      '  not' ' exist: ' + repository_name)

  return sorted(list(_dirty_roles[repository_name]))



def mark_dirty(roles, repository_name='default'):
  """
  <Purpose>
    Mark the list of 'roles' as dirty.

  <Arguments>
    repository_name:
      The name of the repository to get the dirty roles.  If not supplied, the
      'default' repository is searched.

    roles:
      A list of roles that should be marked as dirty.

  <Exceptions>
    securesystemslib.exceptions.FormatError, if the arguments are improperly
    formatted.

    securesystemslib.exceptions.InvalidNameError, if 'repository_name' does not
    exist in the role database.

  <Side Effects>
    None.

  <Returns>
    None.
  """

  # Are the arguments properly formatted?  If not, raise
  # securesystemslib.exceptions.FormatError.
  securesystemslib.formats.NAMES_SCHEMA.check_match(roles)
  securesystemslib.formats.NAME_SCHEMA.check_match(repository_name)

  global _roledb_dict
  global _dirty_roles

  if repository_name not in _roledb_dict or repository_name not in _dirty_roles:
    raise securesystemslib.exceptions.InvalidNameError('Repository name does'
      ' not' ' exist: ' + repository_name)

  _dirty_roles[repository_name].update(roles)



def unmark_dirty(roles, repository_name='default'):
  """
  <Purpose>
    No longer mark the roles in 'roles' as dirty.

  <Arguments>
    repository_name:
      The name of the repository to get the dirty roles.  If not supplied, the
      'default' repository is searched.

    roles:
      A list of roles that should no longer be marked as dirty.

  <Exceptions>
    securesystemslib.exceptions.FormatError, if the arguments are improperly
    formatted.

    securesystemslib.exceptions.InvalidNameError, if 'repository_name' does not
    exist in the role database.

  <Side Effects>
    None.

  <Returns>
    None.
  """

  # Are the arguments properly formatted?  If not, raise
  # securesystemslib.exceptions.FormatError.
  securesystemslib.formats.NAMES_SCHEMA.check_match(roles)
  securesystemslib.formats.NAME_SCHEMA.check_match(repository_name)

  global _roledb_dict
  global _dirty_roles

  if repository_name not in _roledb_dict or repository_name not in _dirty_roles:
    raise securesystemslib.exceptions.InvalidNameError('Repository name does'
      ' not exist: ' + repository_name)

  for role in roles:
    try:
      _dirty_roles[repository_name].remove(role)

    except (KeyError, ValueError):
      logger.debug(repr(role) + ' is not dirty.')



def role_exists(rolename, repository_name='default'):
  """
  <Purpose>
    Verify whether 'rolename' is stored in the role database.

  <Arguments>
    rolename:
      An object representing the role's name, conformant to 'ROLENAME_SCHEMA'
      (e.g., 'root', 'snapshot', 'timestamp').

    repository_name:
      The name of the repository to check whether 'rolename' exists.  If not
      supplied, the 'default' repository is searched.

  <Exceptions>
    securesystemslib.exceptions.FormatError, if 'rolename' does not have the
    correct object format.

    securesystemslib.exceptions.InvalidNameError, if 'rolename' is incorrectly
    formatted, or 'repository_name' does not exist in the role database.

  <Side Effects>
    None.

  <Returns>
    Boolean.  True if 'rolename' is found in the role database, False otherwise.
  """

  # Raise securesystemslib.exceptions.FormatError,
  # securesystemslib.exceptions.InvalidNameError if the arguments are invalid.
  # We do not intercept securesystemslib.exceptions.FormatError
  # or securesystemslib.exceptions.InvalidNameError exceptions.
  try:
    _check_rolename(rolename, repository_name)

  except tuf.exceptions.UnknownRoleError:
    return False

  return True





def remove_role(rolename, repository_name='default'):
  """
  <Purpose>
    Remove 'rolename'.  Delegated roles were previously removed as well,
    but this step is longer supported since the repository can resemble
    a graph of delegations.  That is, we shouldn't delete rolename's
    delegations because another role may have a valid delegation
    to it, whereas before the only valid delegation to it must be from
    'rolename' (repository resembles a tree of delegations).

  <Arguments>
    rolename:
      An object representing the role's name, conformant to 'ROLENAME_SCHEMA'
      (e.g., 'root', 'snapshot', 'timestamp').

    repository_name:
      The name of the repository to remove the role.  If not supplied, the
      'default' repository is searched.

  <Exceptions>
    securesystemslib.exceptions.FormatError, if 'rolename' does not have the
    correct object format.

    tuf.exceptions.UnknownRoleError, if 'rolename' cannot be found
    in the role database.

    securesystemslib.exceptions.InvalidNameError, if 'rolename' is incorrectly
    formatted, or 'repository_name' does not exist in the role database.

  <Side Effects>
    A role may be removed from the role database.

  <Returns>
    None.
  """

  # Does 'repository_name' have the correct format?  Raise
  # 'securesystemslib.exceptions.FormatError' if it is improperly formatted.
  securesystemslib.formats.NAME_SCHEMA.check_match(repository_name)

  # Raises securesystemslib.exceptions.FormatError,
  # tuf.exceptions.UnknownRoleError, or
  # securesystemslib.exceptions.InvalidNameError.
  _check_rolename(rolename, repository_name)

  global _roledb_dict
  global _dirty_roles

  # 'rolename' was verified to exist in _check_rolename().
  # Remove 'rolename' now.
  del _roledb_dict[repository_name][rolename]





def get_rolenames(repository_name='default'):
  """
  <Purpose>
    Return a list of the rolenames found in the role database.

  <Arguments>
    repository_name:
      The name of the repository to get the rolenames.  If not supplied, the
      'default' repository is searched.

  <Exceptions>
    securesystemslib.exceptions.FormatError, if 'repository_name' is improperly
    formatted.

    securesystemslib.exceptions.InvalidNameError, if 'repository_name' does not
    exist in the role database.

  <Side Effects>
    None.

  <Returns>
    A list of rolenames.
  """

  # Does 'repository_name' have the correct format?  Raise
  # 'securesystemslib.exceptions.FormatError' if it is improperly formatted.
  securesystemslib.formats.NAME_SCHEMA.check_match(repository_name)

  global _roledb_dict
  global _dirty_roles

  if repository_name not in _roledb_dict or repository_name not in _dirty_roles:
    raise securesystemslib.exceptions.InvalidNameError('Repository name does'
      ' not' ' exist: ' + repository_name)

  return list(_roledb_dict[repository_name].keys())





def get_roleinfo(rolename, repository_name='default'):
  """
  <Purpose>
    Return the roleinfo of 'rolename'.

    {'keyids': ['34345df32093bd12...'],
     'threshold': 1,
     'signatures': ['ab453bdf...', ...],
     'paths': ['path/to/target1', 'path/to/target2', ...],
     'path_hash_prefixes': ['a324fcd...', ...],
     'delegations': {'keys': {}, 'roles': []}}

    The 'signatures', 'paths', 'path_hash_prefixes', and 'delegations' dict keys
    are optional.

  <Arguments>
    rolename:
      An object representing the role's name, conformant to 'ROLENAME_SCHEMA'
      (e.g., 'root', 'snapshot', 'timestamp').

    repository_name:
      The name of the repository to get the role info.  If not supplied, the
      'default' repository is searched.

  <Exceptions>
    securesystemslib.exceptions.FormatError, if the arguments are improperly
    formatted.

    tuf.exceptions.UnknownRoleError, if 'rolename' does not exist.

    securesystemslib.exceptions.InvalidNameError, if 'rolename' is incorrectly
    formatted, or 'repository_name' does not exist in the role database.


  <Side Effects>
    None.

  <Returns>
    The roleinfo of 'rolename'.
  """

  # Is 'repository_name' properly formatted?  If not, raise
  # 'securesystemslib.exceptions.FormatError'.
  securesystemslib.formats.NAME_SCHEMA.check_match(repository_name)

  # Raises securesystemslib.exceptions.FormatError,
  # tuf.exceptions.UnknownRoleError, or
  # securesystemslib.exceptions.InvalidNameError.
  _check_rolename(rolename, repository_name)

  global _roledb_dict
  global _dirty_roles

  return copy.deepcopy(_roledb_dict[repository_name][rolename])





def get_role_keyids(rolename, repository_name='default'):
  """
  <Purpose>
    Return a list of the keyids associated with 'rolename'.  Keyids are used as
    identifiers for keys (e.g., rsa key).  A list of keyids are associated with
    each rolename.  Signing a metadata file, such as 'root.json' (Root role),
    involves signing or verifying the file with a list of keys identified by
    keyid.

  <Arguments>
    rolename:
      An object representing the role's name, conformant to 'ROLENAME_SCHEMA'
      (e.g., 'root', 'snapshot', 'timestamp').

    repository_name:
      The name of the repository to get the role keyids.  If not supplied, the
      'default' repository is searched.

  <Exceptions>
    securesystemslib.exceptions.FormatError, if the arguments do not have the
    correct object format.

    tuf.exceptions.UnknownRoleError, if 'rolename' cannot be found
    in the role database.

    securesystemslib.exceptions.InvalidNameError, if 'rolename' is incorrectly
    formatted, or 'repository_name' does not exist in the role database.

  <Side Effects>
    None.

  <Returns>
    A list of keyids.
  """

  # Raise 'securesystemslib.exceptions.FormatError' if 'repository_name' is
  # improperly formatted.
  securesystemslib.formats.NAME_SCHEMA.check_match(repository_name)

  # Raises securesystemslib.exceptions.FormatError,
  # tuf.exceptions.UnknownRoleError, or
  # securesystemslib.exceptions.InvalidNameError.
  _check_rolename(rolename, repository_name)

  global _roledb_dict
  global _dirty_roles

  roleinfo = _roledb_dict[repository_name][rolename]

  return roleinfo['keyids']





def get_role_threshold(rolename, repository_name='default'):
  """
  <Purpose>
    Return the threshold value of the role associated with 'rolename'.

  <Arguments>
    rolename:
      An object representing the role's name, conformant to 'ROLENAME_SCHEMA'
      (e.g., 'root', 'snapshot', 'timestamp').

    repository_name:
      The name of the repository to get the role threshold.  If not supplied,
      the 'default' repository is searched.


  <Exceptions>
    securesystemslib.exceptions.FormatError, if the arguments do not have the
    correct object format.

    tuf.exceptions.UnknownRoleError, if 'rolename' cannot be found
    in the role database.

    securesystemslib.exceptions.InvalidNameError, if 'rolename' is incorrectly
    formatted, or 'repository_name' does not exist in the role database.

  <Side Effects>
    None.

  <Returns>
    A threshold integer value.
  """

  # Raise 'securesystemslib.exceptions.FormatError' if 'repository_name' is
  # improperly formatted.
  securesystemslib.formats.NAME_SCHEMA.check_match(repository_name)

  # Raises securesystemslib.exceptions.FormatError,
  # tuf.exceptions.UnknownRoleError, or
  # securesystemslib.exceptions.InvalidNameError.
  _check_rolename(rolename, repository_name)

  global _roledb_dict
  global _dirty_roles

  roleinfo = _roledb_dict[repository_name][rolename]

  return roleinfo['threshold']





def get_role_paths(rolename, repository_name='default'):
  """
  <Purpose>
    Return the paths of the role associated with 'rolename'.

  <Arguments>
    rolename:
      An object representing the role's name, conformant to 'ROLENAME_SCHEMA'
      (e.g., 'root', 'snapshot', 'timestamp').

    repository_name:
      The name of the repository to get the role paths.  If not supplied, the
      'default' repository is searched.

  <Exceptions>
    securesystemslib.exceptions.FormatError, if the arguments do not have the
    correct object format.

    tuf.exceptions.UnknownRoleError, if 'rolename' cannot be found
    in the role database.

    securesystemslib.exceptions.InvalidNameError, if 'rolename' is incorrectly
    formatted, or 'repository_name' does not exist in the role database.

  <Side Effects>
    None.

  <Returns>
    A list of paths.
  """

  # Raise 'securesystemslib.exceptions.FormatError' if 'repository_name' is
  # improperly formatted.
  securesystemslib.formats.NAME_SCHEMA.check_match(repository_name)

  # Raises securesystemslib.exceptions.FormatError,
  # tuf.exceptions.UnknownRoleError, or
  # securesystemslib.exceptions.InvalidNameError.
  _check_rolename(rolename, repository_name)

  global _roledb_dict
  global _dirty_roles

  roleinfo = _roledb_dict[repository_name][rolename]

  # Paths won't exist for non-target roles.
  try:
    return roleinfo['paths']

  except KeyError:
    return dict()





def get_delegated_rolenames(rolename, repository_name='default'):
  """
  <Purpose>
    Return the delegations of a role.  If 'rolename' is 'tuf' and the role
    database contains ['django', 'requests', 'cryptography'], in 'tuf's
    delegations field, return ['django', 'requests', 'cryptography'].

  <Arguments>
    rolename:
      An object representing the role's name, conformant to 'ROLENAME_SCHEMA'
      (e.g., 'root', 'snapshot', 'timestamp').

    repository_name:
      The name of the repository to get the delegated rolenames.  If not
      supplied, the 'default' repository is searched.

  <Exceptions>
    securesystemslib.exceptions.FormatError, if the arguments do not have the
    correct object format.

    tuf.exceptions.UnknownRoleError, if 'rolename' cannot be found
    in the role database.

    securesystemslib.exceptions.InvalidNameError, if 'rolename' is incorrectly
    formatted, or 'repository_name' does not exist in the role database.

  <Side Effects>
    None.

  <Returns>
    A list of rolenames. Note that the rolenames are *NOT* sorted by order of
    delegation.
  """


  # Does 'repository_name' have the correct format?  Raise
  # 'securesystemslib.exceptions.FormatError' if it does not.
  securesystemslib.formats.NAME_SCHEMA.check_match(repository_name)

  # Raises securesystemslib.exceptions.FormatError,
  # tuf.exceptions.UnknownRoleError, or
  # securesystemslib.exceptions.InvalidNameError.
  _check_rolename(rolename, repository_name)

  global _roledb_dict
  global _dirty_roles

  # get_roleinfo() raises a 'securesystemslib.exceptions.InvalidNameError' if
  # 'repository_name' does not exist in the role database.
  roleinfo = get_roleinfo(rolename, repository_name)
  delegated_roles = []

  for delegated_role in roleinfo['delegations']['roles']:
    delegated_roles.append(delegated_role['name'])

  return delegated_roles





def clear_roledb(repository_name='default', clear_all=False):
  """
  <Purpose>
    Reset the roledb database.

  <Arguments>
    repository_name:
      The name of the repository to clear.  If not supplied, the 'default'
      repository is cleared.

    clear_all:
      Boolean indicating whether to clear the entire roledb.

  <Exceptions>
    securesystemslib.exceptions.FormatError, if 'repository_name' does not have
    the correct format.

    securesystemslib.exceptions.InvalidNameError, if 'repository_name' does not
    exist in the role database.

  <Side Effects>
    None.

  <Returns>
    None.
  """

  # Do the arguments have the correct format?  If not, raise
  # 'securesystemslib.exceptions.FormatError'
  securesystemslib.formats.NAME_SCHEMA.check_match(repository_name)
  securesystemslib.formats.BOOLEAN_SCHEMA.check_match(clear_all)

  global _roledb_dict
  global _dirty_roles

  if repository_name not in _roledb_dict or repository_name not in _dirty_roles:
    raise securesystemslib.exceptions.InvalidNameError('Repository name does not'
      ' exist: ' + repository_name)

  if clear_all:
    _roledb_dict = {}
    _roledb_dict['default'] = {}
    _dirty_roles = {}
    _dirty_roles['default'] = set()
    return

  _roledb_dict[repository_name] = {}
  _dirty_roles[repository_name] = set()





def _check_rolename(rolename, repository_name='default'):
  """ Raise securesystemslib.exceptions.FormatError if 'rolename' does not match
  'tuf.formats.ROLENAME_SCHEMA',
  tuf.exceptions.UnknownRoleError if 'rolename' is not found in the
  role database, or securesystemslib.exceptions.InvalidNameError if
  'repository_name' does not exist in the role database.
  """

  # Does 'rolename' have the correct object format?
  # This check will ensure 'rolename' has the appropriate number of objects
  # and object types, and that all dict keys are properly named.
  tuf.formats.ROLENAME_SCHEMA.check_match(rolename)

  # Does 'repository_name' have the correct format?
  securesystemslib.formats.NAME_SCHEMA.check_match(repository_name)

  # Raises securesystemslib.exceptions.InvalidNameError.
  _validate_rolename(rolename)

  global _roledb_dict
  global _dirty_roles

  if repository_name not in _roledb_dict or repository_name not in _dirty_roles:
    raise securesystemslib.exceptions.InvalidNameError('Repository name does not'
      ' exist: ' + repository_name)

  if rolename not in _roledb_dict[repository_name]:
    raise tuf.exceptions.UnknownRoleError('Role name does not exist: ' + rolename)





def _validate_rolename(rolename):
  """
  Raise securesystemslib.exceptions.InvalidNameError if 'rolename' is not
  formatted correctly.  It is assumed 'rolename' has been checked against
  'ROLENAME_SCHEMA' prior to calling this function.  """

  if rolename == '':
    raise securesystemslib.exceptions.InvalidNameError('Rolename must *not* be'
      ' an empty string.')

  if rolename != rolename.strip():
    raise securesystemslib.exceptions.InvalidNameError('Invalid rolename.'
      '  Cannot start or end with whitespace: ' + rolename)

  if rolename.startswith('/') or rolename.endswith('/'):
    raise securesystemslib.exceptions.InvalidNameError('Invalid rolename.'
      '  Cannot start or end with a "/": ' + rolename)

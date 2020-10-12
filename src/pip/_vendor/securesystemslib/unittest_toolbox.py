"""
<Program>
  unittest_toolbox.py

<Author>
  Konstantin Andrianov.

<Started>
  March 26, 2012.

<Copyright>
  See LICENSE for licensing information.

<Purpose>
  Provides an array of various methods for unit testing.  Use it instead of
  actual unittest module.  This module builds on unittest module.
  Specifically, Modified_TestCase is a derived class from unittest.TestCase.
"""

# Help with Python 3 compatibility, where the print statement is a function, an
# implicit relative import is invalid, and the '/' operator performs true
# division.  Example:  print 'hello world' raises a 'SyntaxError' exception.
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os
import sys
import shutil
import unittest
import tempfile
import random
import string


class Modified_TestCase(unittest.TestCase):
  """
  <Purpose>
    Provide additional test-setup methods to make testing
    of module's methods-under-test as independent as possible.

    If you want to modify setUp()/tearDown() do:
    class Your_Test_Class(modified_TestCase):
      def setUp():
        your setup modification
        your setup modification
        ...
        modified_TestCase.setUp(self)

  <Methods>
    make_temp_directory(self, directory=None):
      Creates and returns an absolute path of a temporary directory.

    make_temp_file(self, suffix='.txt', directory=None):
      Creates and returns an absolute path of an empty temp file.

    make_temp_data_file(self, suffix='', directory=None, data = junk_data):
      Returns an absolute path of a temp file containing some data.

    random_path(self, length = 7):
      Generate a 'random' path consisting of n-length strings of random chars.


    Static Methods:
    --------------
    Following methods are static because they technically don't operate
    on any instances of the class, what they do is: they modify class variables
    (dictionaries) that are shared among all instances of the class.  So
    it is possible to call them without instantiating the class.

    random_string(length=7):
      Generate a 'length' long string of random characters.
  """


  def setUp(self):
    self._cleanup = []



  def tearDown(self):
    for cleanup_function in self._cleanup:
      # Perform clean up by executing clean-up functions.
      try:
        # OSError will occur if the directory was already removed.
        cleanup_function()

      except OSError:
        pass



  def make_temp_directory(self, directory=None):
    """Creates and returns an absolute path of a directory."""
    prefix = self.__class__.__name__+'_'
    temp_directory = tempfile.mkdtemp(prefix=prefix, dir=directory)

    def _destroy_temp_directory():
      shutil.rmtree(temp_directory)
    self._cleanup.append(_destroy_temp_directory)
    return temp_directory



  def make_temp_file(self, suffix='.txt', directory=None):
    """Creates and returns an absolute path of an empty file."""

    prefix='tmp_file_'+self.__class__.__name__+'_'
    temp_file = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=directory)

    def _destroy_temp_file():
      os.unlink(temp_file[1])
    self._cleanup.append(_destroy_temp_file)
    return temp_file[1]



  def make_temp_data_file(self, suffix='', directory=None, data = 'junk data'):
    """Returns an absolute path of a temp file containing data."""

    temp_file_path = self.make_temp_file(suffix=suffix, directory=directory)
    temp_file = open(temp_file_path, 'wt')
    temp_file.write(data)
    temp_file.close()

    return temp_file_path



  def random_path(self, length = 7):
    """Generate a 'random' path consisting of random n-length strings."""

    rand_path = '/'+self.random_string(length)
    for i in range(2):
      rand_path = os.path.join(rand_path, self.random_string(length))

    return rand_path



  @staticmethod
  def random_string(length=15):
    """Generate a random string of specified length."""

    rand_str = ''
    for letter in range(length):
      rand_str += random.choice('abcdefABCDEF' +string.digits)

    return rand_str

#!/usr/bin/env python

"""
<Program Name>
  schema.py

<Author>
  Geremy Condra
  Vladimir Diaz <vladimir.v.diaz@gmail.com>

<Started>
  Refactored April 30, 2012 (previously named checkjson.py). -Vlad

<Copyright>
  See LICENSE for licensing information.

<Purpose>
  Provide a variety of classes that compare objects
  based on their format and determine if they match.
  These classes, or schemas, do not simply check the
  type of the objects being compared, but inspect
  additional aspects of the objects like names and
  the number of items included.
  For example:
  >>> good = {'first': 'Marty', 'last': 'McFly'}
  >>> bad = {'sdfsfd': 'Biff', 'last': 'Tannen'}
  >>> bad = {'sdfsfd': 'Biff', 'last': 'Tannen'}
  >>> schema = Object(first=AnyString(), last=AnyString())
  >>> schema.matches(good)
  True
  >>> schema.matches(bad)
  False

  In the process of determining if the two objects matched the template,
  securesystemslib.schema.Object() inspected the named keys of both
  dictionaries.  In the case of the 'bad' dict, a 'first' dict key could not be
  found.  As a result, 'bad' was flagged a mismatch.

  'schema.py' provides additional schemas for testing objects based on other
  criteria.  See 'securesystemslib.formats.py' and the rest of this module for
  extensive examples.  Anything related to the checking of securesystemslib
  objects and their formats can be found in 'formats.py'.
"""

# Help with Python 3 compatibility, where the print statement is a function, an
# implicit relative import is invalid, and the '/' operator performs true
# division.  Example:  print 'hello world' raises a 'SyntaxError' exception.
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import re
import sys

from pip._vendor import six

class _Dummy(object):
  pass
securesystemslib = _Dummy()
from pip._vendor.securesystemslib import exceptions as _securesystemslib_exceptions
securesystemslib.exceptions = _securesystemslib_exceptions


class Schema:
  """
  <Purpose>
    A schema matches a set of possible Python objects, of types
    that are encodable in JSON.  'Schema' is the base class for
    the other classes defined in this module.  All derived classes
    should implement check_match().
  """

  def matches(self, object):
    """
    <Purpose>
      Return True if 'object' matches this schema, False if it doesn't.
      If the caller wishes to signal an error on a failed match, check_match()
      should be called, which will raise a 'exceptions.FormatError' exception.
    """

    try:
      self.check_match(object)
    except securesystemslib.exceptions.FormatError:
      return False
    else:
      return True


  def check_match(self, object):
    """
    <Purpose>
      Abstract method.  Classes that inherit from 'Schema' must
      implement check_match().  If 'object' matches the schema, check_match()
      should simply return.  If 'object' does not match the schema,
      'exceptions.FormatError' should be raised.
    """

    raise NotImplementedError()





class Any(Schema):
  """
  <Purpose>
    Matches any single object.  Whereas other schemas explicitly state
    the required type of its argument, Any() does not. It simply does a
    'pass' when 'check_match()' is called and at the point where the schema
    is instantiated.

    Supported methods include:
      matches(): returns a Boolean result.
      check_match(): passed

  <Example Use>

    >>> schema = Any()
    >>> schema.matches('A String')
    True
    >>> schema.matches([1, 'list'])
    True
  """

  def __init__(self):
    pass


  def check_match(self, object):
    pass





class String(Schema):
  """
  <Purpose>
    Matches a particular string.  The argument object must be a string and be
    equal to a specific string value.  At instantiation, the string is set and
    any future comparisons are checked against this internal string value.

    Supported methods include:
      matches(): returns a Boolean result.
      check_match(): raises 'exceptions.FormatError' on a mismatch.

  <Example Use>

    >>> schema = String('Hi')
    >>> schema.matches('Hi')
    True
    >>> schema.matches('Not hi')
    False
  """

  def __init__(self, string):
    if not isinstance(string, six.string_types):
      raise securesystemslib.exceptions.FormatError('Expected a string but'
          ' got ' + repr(string))

    self._string = string


  def check_match(self, object):
    if self._string != object:
      raise securesystemslib.exceptions.FormatError(
          'Expected ' + repr(self._string) + ' got ' + repr(object))





class AnyString(Schema):
  """
  <Purpose>
    Matches any string, but not a non-string object.  This schema
    can be viewed as the Any() schema applied to Strings, but an
    additional check is performed to ensure only strings are considered.

    Supported methods include:
      matches(): returns a Boolean result.
      check_match(): raises 'exceptions.FormatError' on a mismatch.

  <Example Use>

    >>> schema = AnyString()
    >>> schema.matches('')
    True
    >>> schema.matches('a string')
    True
    >>> schema.matches(['a'])
    False
    >>> schema.matches(3)
    False
    >>> schema.matches(u'a unicode string')
    True
    >>> schema.matches({})
    False
  """

  def __init__(self):
    pass


  def check_match(self, object):
    if not isinstance(object, six.string_types):
      raise securesystemslib.exceptions.FormatError('Expected a string'
          ' but got ' + repr(object))





class AnyNonemptyString(AnyString):
  """
  <Purpose>
    Matches any string with one or more characters.
    This schema can be viewed as the Any() schema applied to Strings, but an
    additional check is performed to ensure only strings are considered and
    that said strings have at least one character.

    Supported methods include:
      matches(): returns a Boolean result.
      check_match(): raises 'exceptions.FormatError' on a mismatch.

  <Example Use>

    >>> schema = AnyNonemptyString()
    >>> schema.matches('')
    False
    >>> schema.matches('a string')
    True
    >>> schema.matches(['a'])
    False
    >>> schema.matches(3)
    False
    >>> schema.matches(u'a unicode string')
    True
    >>> schema.matches({})
    False
  """

  def check_match(self, object):
    AnyString.check_match(self, object)

    if object == "":
        raise securesystemslib.exceptions.FormatError('Expected a string'
            ' with at least one character but got ' + repr(object))





class AnyBytes(Schema):
  """
  <Purpose>
    Matches any byte string, but not a non-byte object.  This schema can be
    viewed as the Any() schema applied to byte strings, but an additional check
    is performed to ensure only strings are considered.  Supported methods
    include:
      matches(): returns a Boolean result.
      check_match(): raises 'exceptions.FormatError' on a mismatch.

  <Example Use>

    >>> schema = AnyBytes()
    >>> schema.matches(b'')
    True
    >>> schema.matches(b'a string')
    True
    >>> schema.matches(['a'])
    False
    >>> schema.matches(3)
    False
    >>> schema.matches({})
    False
  """

  def __init__(self):
    pass


  def check_match(self, object):
    if not isinstance(object, six.binary_type):
      raise securesystemslib.exceptions.FormatError('Expected a byte string'
          ' but got ' + repr(object))





class LengthString(Schema):
  """
  <Purpose>
    Matches any string of a specified length.  The argument object must be a
    string.  At instantiation, the string length is set and any future
    comparisons are checked against this internal string value length.

    Supported methods include:
      matches(): returns a Boolean result.
      check_match(): raises 'exceptions.FormatError' on a mismatch.

  <Example Use>

    >>> schema = LengthString(5)
    >>> schema.matches('Hello')
    True
    >>> schema.matches('Hi')
    False
  """

  def __init__(self, length):
    if isinstance(length, bool) or not isinstance(length, six.integer_types):
      # We need to check for bool as a special case, since bool
      # is for historical reasons a subtype of int.
      raise securesystemslib.exceptions.FormatError(
          'Got ' + repr(length) + ' instead of an integer.')

    self._string_length = length


  def check_match(self, object):
    if not isinstance(object, six.string_types):
      raise securesystemslib.exceptions.FormatError('Expected a string but'
          ' got ' + repr(object))

    if len(object) != self._string_length:
      raise securesystemslib.exceptions.FormatError('Expected a string of'
          ' length ' + repr(self._string_length))





class LengthBytes(Schema):
  """
  <Purpose>
    Matches any Bytes of a specified length.  The argument object must be either
    a str() in Python 2, or bytes() in Python 3.  At instantiation, the bytes
    length is set and any future comparisons are checked against this internal
    bytes value length.

    Supported methods include:
      matches(): returns a Boolean result.
      check_match(): raises 'exceptions.FormatError' on a mismatch.

  <Example Use>

    >>> schema = LengthBytes(5)
    >>> schema.matches(b'Hello')
    True
    >>> schema.matches(b'Hi')
    False
  """

  def __init__(self, length):
    if isinstance(length, bool) or not isinstance(length, six.integer_types):
      # We need to check for bool as a special case, since bool
      # is for historical reasons a subtype of int.
      raise securesystemslib.exceptions.FormatError(
          'Got ' + repr(length) + ' instead of an integer.')

    self._bytes_length = length


  def check_match(self, object):
    if not isinstance(object, six.binary_type):
      raise securesystemslib.exceptions.FormatError('Expected a byte but'
          ' got ' + repr(object))

    if len(object) != self._bytes_length:
      raise securesystemslib.exceptions.FormatError('Expected a byte of'
          ' length ' + repr(self._bytes_length))





class OneOf(Schema):
  """
  <Purpose>
    Matches an object that matches any one of several schemas.  OneOf() returns
    a result as soon as one of its recognized sub-schemas is encountered in the
    object argument.  When OneOf() is instantiated, its supported sub-schemas
    are specified by a sequence type (e.g., a list, tuple, etc.).  A mismatch
    is returned after checking all sub-schemas and not finding a supported
    type.

    Supported methods include:
      matches(): returns a Boolean result.
      check_match(): raises 'exceptions.FormatError' on a mismatch.

  <Example Use>
    >>> schema = OneOf([ListOf(Integer()), String('Hello'), String('bye')])
    >>> schema.matches(3)
    False
    >>> schema.matches('bye')
    True
    >>> schema.matches([])
    True
    >>> schema.matches([1,2])
    True
    >>> schema.matches(['Hi'])
    False
  """

  def __init__(self, alternatives):
    # Ensure each item of the list contains the expected object type.
    if not isinstance(alternatives, list):
      raise securesystemslib.exceptions.FormatError('Expected a list but'
          ' got ' + repr(alternatives))

    for alternative in alternatives:
      if not isinstance(alternative, Schema):
        raise securesystemslib.exceptions.FormatError('List contains an'
            ' invalid item ' + repr(alternative))

    self._alternatives = alternatives


  def check_match(self, object):
    # Simply return as soon as we find a match.
    # Raise 'exceptions.FormatError' if no matches are found.
    for alternative in self._alternatives:
      if alternative.matches(object):
        return
    raise securesystemslib.exceptions.FormatError('Object did not match a'
        ' recognized alternative.')





class AllOf(Schema):
  """
  <Purpose>
    Matches the intersection of a list of schemas.  The object being tested
    must match all of the required sub-schemas.  Unlike OneOf(), which can
    return a result as soon as a match is found in one of its supported
    sub-schemas, AllOf() must verify each sub-schema before returning a result.

    Supported methods include:
      matches(): returns a Boolean result.
      check_match(): raises 'exceptions.FormatError' on a mismatch.

  <Example Use>
    >>> schema = AllOf([Any(), AnyString(), String('a')])
    >>> schema.matches('b')
    False
    >>> schema.matches('a')
    True
  """

  def __init__(self, required_schemas):
    # Ensure each item of the list contains the expected object type.
    if not isinstance(required_schemas, list):
      raise securesystemslib.exceptions.FormatError('Expected a list but'
          ' got' + repr(required_schemas))

    for schema in required_schemas:
      if not isinstance(schema, Schema):
        raise securesystemslib.exceptions.FormatError('List contains an'
            ' invalid item ' + repr(schema))

    self._required_schemas = required_schemas[:]


  def check_match(self, object):
    for required_schema in self._required_schemas:
      required_schema.check_match(object)





class Boolean(Schema):
  """
  <Purpose>
    Matches a boolean.  The object argument must be one of True or False.  All
    other types are flagged as mismatches.

    Supported methods include:
      matches(): returns a Boolean result.
      check_match(): raises 'exceptions.FormatError' on a mismatch.

  <Example Use>
    >>> schema = Boolean()
    >>> schema.matches(True) and schema.matches(False)
    True
    >>> schema.matches(11)
    False
 """

  def __init__(self):
    pass


  def check_match(self, object):
    if not isinstance(object, bool):
      raise securesystemslib.exceptions.FormatError(
          'Got ' + repr(object) + ' instead of a boolean.')





class ListOf(Schema):
  """
  <Purpose>
    Matches a homogeneous list of some sub-schema.  That is, all the sub-schema
    must be of the same type.  The object argument must be a sequence type
    (e.g., a list, tuple, etc.).  When ListOf() is instantiated, a minimum and
    maximum count can be specified for the homogeneous sub-schema list.  If
    min_count is set to 'n', the object argument sequence must contain 'n'
    items.  See ListOf()'s __init__ method for the expected arguments.

    Supported methods include:
      matches(): returns a Boolean result.
      check_match(): raises 'exceptions.FormatError' on a mismatch.

  <Example Use>
    >>> schema = ListOf(RegularExpression('(?:..)*'))
    >>> schema.matches('hi')
    False
    >>> schema.matches([])
    True
    >>> schema.matches({})
    False
    >>> schema.matches(['Hi', 'this', 'list', 'is', 'full', 'of', 'even', 'strs'])
    True
    >>> schema.matches(['This', 'one', 'is not'])
    False
    >>> schema = ListOf(Integer(), min_count=3, max_count=10)
    >>> schema.matches([3]*2)
    False
    >>> schema.matches([3]*3)
    True
    >>> schema.matches([3]*10)
    True
    >>> schema.matches([3]*11)
    False
  """

  def __init__(self, schema, min_count=0, max_count=sys.maxsize, list_name='list'):
    """
    <Purpose>
      Create a new ListOf schema.

    <Arguments>
      schema:  The pattern to match.
      min_count: The minimum number of sub-schema in 'schema'.
      max_count: The maximum number of sub-schema in 'schema'.
      list_name: A string identifier for the ListOf object.
    """

    if not isinstance(schema, Schema):
      message = 'Expected Schema type but got '+repr(schema)
      raise securesystemslib.exceptions.FormatError(message)

    self._schema = schema
    self._min_count = min_count
    self._max_count = max_count
    self._list_name = list_name


  def check_match(self, object):
    if not isinstance(object, (list, tuple)):
      raise securesystemslib.exceptions.FormatError(
          'Expected object of type {} but got type {}'.format(
            self._list_name, type(object).__name__))


    # Check if all the items in the 'object' list
    # match 'schema'.
    for item in object:
      try:
        self._schema.check_match(item)

      except securesystemslib.exceptions.FormatError as e:
        raise securesystemslib.exceptions.FormatError(
            str(e) + ' in ' + repr(self._list_name))

    # Raise exception if the number of items in the list is
    # not within the expected range.
    if not (self._min_count <= len(object) <= self._max_count):
        raise securesystemslib.exceptions.FormatError(
            'Length of ' + repr(self._list_name) + ' out of range.')





class Integer(Schema):
  """
  <Purpose>
    Matches an integer.  A range can be specified.  For example, only integers
    between 8 and 42 can be set as a requirement.  The object argument is also
    checked against a Boolean type, since booleans have historically been
    considered a sub-type of integer.

    Supported methods include:
      matches(): returns a Boolean result.
      check_match(): raises 'exceptions.FormatError' on a mismatch.

  <Example Use>
    >>> schema = Integer()
    >>> schema.matches(99)
    True
    >>> schema.matches(False)
    False
    >>> schema.matches('a string')
    False
    >>> Integer(lo=10, hi=30).matches(25)
    True
    >>> Integer(lo=10, hi=30).matches(5)
    False
  """

  def __init__(self, lo = -2147483648, hi = 2147483647):
    """
    <Purpose>
      Create a new Integer schema.

    <Arguments>
      lo: The minimum value the int object argument can be.
      hi: The maximum value the int object argument can be.
    """

    self._lo = lo
    self._hi = hi


  def check_match(self, object):
    if isinstance(object, bool) or not isinstance(object, six.integer_types):
      # We need to check for bool as a special case, since bool
      # is for historical reasons a subtype of int.
      raise securesystemslib.exceptions.FormatError(
          'Got ' + repr(object) + ' instead of an integer.')

    elif not (self._lo <= object <= self._hi):
      int_range = '[' + repr(self._lo) + ', ' + repr(self._hi) + '].'
      raise securesystemslib.exceptions.FormatError(
          repr(object) + ' not in range ' + int_range)





class DictOf(Schema):
  """
  <Purpose>
    Matches a mapping from items matching a particular key-schema to items
    matching a value-schema (i.e., the object being checked must be a dict).
    Note that in JSON, keys must be strings.  In the example below, the keys of
    the dict must be one of the letters contained in 'aeiou' and the value must
    be a structure containing any two strings.

    Supported methods include:
      matches(): returns a Boolean result.
      check_match(): raises 'exceptions.FormatError' on a mismatch.

  <Example Use>
    >>> schema = DictOf(RegularExpression(r'[aeiou]+'), Struct([AnyString(), AnyString()]))
    >>> schema.matches('')
    False
    >>> schema.matches({})
    True
    >>> schema.matches({'a': ['x', 'y'], 'e' : ['', '']})
    True
    >>> schema.matches({'a': ['x', 3], 'e' : ['', '']})
    False
    >>> schema.matches({'a': ['x', 'y'], 'e' : ['', ''], 'd' : ['a', 'b']})
    False
  """

  def __init__(self, key_schema, value_schema):
    """
    <Purpose>
      Create a new DictOf schema.

    <Arguments>
      key_schema:  The dictionary's key.
      value_schema: The dictionary's value.
    """

    if not isinstance(key_schema, Schema):
      raise securesystemslib.exceptions.FormatError('Expected Schema but'
          ' got ' + repr(key_schema))

    if not isinstance(value_schema, Schema):
      raise securesystemslib.exceptions.FormatError('Expected Schema but'
          ' got ' + repr(value_schema))

    self._key_schema = key_schema
    self._value_schema = value_schema


  def check_match(self, object):
    if not isinstance(object, dict):
      raise securesystemslib.exceptions.FormatError('Expected a dict but'
          ' got ' + repr(object))

    for key, value in six.iteritems(object):
      self._key_schema.check_match(key)
      self._value_schema.check_match(value)





class Optional(Schema):
  """
  <Purpose>
    Provide a way for the Object() schema to accept optional dictionary keys.
    The Object() schema outlines how a dictionary should look, such as the
    names for dict keys and the object type of the dict values.  Optional()'s
    intended use is as a sub-schema to Object().  Object() flags an object as a
    mismatch if a required key is not encountered, however, dictionary keys
    labeled Optional() are not required to appear in the object's list of
    required keys.  If an Optional() key IS found, Optional()'s sub-schemas are
    then verified.

    Supported methods include:
      matches(): returns a Boolean result.
      check_match(): raises 'exceptions.FormatError' on a mismatch.

  <Example Use>
    >>> schema = Object(k1=String('X'), k2=Optional(String('Y')))
    >>> schema.matches({'k1': 'X', 'k2': 'Y'})
    True
    >>> schema.matches({'k1': 'X', 'k2': 'Z'})
    False
    >>> schema.matches({'k1': 'X'})
    True
  """

  def __init__(self, schema):
    if not isinstance(schema, Schema):
      raise securesystemslib.exceptions.FormatError('Expected Schema, but'
          ' got ' + repr(schema))
    self._schema = schema


  def check_match(self, object):
    self._schema.check_match(object)





class Object(Schema):
  """
  <Purpose>
    Matches a dict from specified keys to key-specific types.  Unrecognized
    keys are allowed.  The Object() schema outlines how a dictionary should
    look, such as the names for dict keys and the object type of the dict
    values.  See schema.Optional() to learn how Object() incorporates optional
    sub-schemas.

    Supported methods include:
      matches(): returns a Boolean result.
      check_match(): raises 'exceptions.FormatError' on a mismatch.

  <Example Use>
    >>> schema = Object(a=AnyString(), bc=Struct([Integer(), Integer()]))
    >>> schema.matches({'a':'ZYYY', 'bc':[5,9]})
    True
    >>> schema.matches({'a':'ZYYY', 'bc':[5,9], 'xx':5})
    True
    >>> schema.matches({'a':'ZYYY', 'bc':[5,9,3]})
    False
    >>> schema.matches({'a':'ZYYY'})
    False
  """

  def __init__(self, object_name='object', **required):
    """
    <Purpose>
      Create a new Object schema.

    <Arguments>
      object_name: A string identifier for the object argument.

      A variable number of keyword arguments is accepted.
    """

    # Ensure valid arguments.
    for key, schema in six.iteritems(required):
      if not isinstance(schema, Schema):
        raise securesystemslib.exceptions.FormatError('Expected Schema but'
            ' got ' + repr(schema))

    self._object_name = object_name
    self._required = list(required.items())


  def check_match(self, object):
    if not isinstance(object, dict):
      raise securesystemslib.exceptions.FormatError(
          'Wanted a ' + repr(self._object_name) + '.')

    # (key, schema) = (a, AnyString()) = (a=AnyString())
    for key, schema in self._required:
      # Check if 'object' has all the required dict keys.  If not one of the
      # required keys, check if it is an Optional().
      try:
        item = object[key]

      except KeyError:
        # If not an Optional schema, raise an exception.
        if not isinstance(schema, Optional):
          message = 'Missing key ' + repr(key) + ' in ' + repr(self._object_name)
          raise securesystemslib.exceptions.FormatError(
              'Missing key ' + repr(key) + ' in ' + repr(self._object_name))

      # Check that 'object's schema matches Object()'s schema for this
      # particular 'key'.
      else:
        try:
          schema.check_match(item)

        except securesystemslib.exceptions.FormatError as e:
          raise securesystemslib.exceptions.FormatError(
              str(e) + ' in ' + self._object_name + '.' + key)





class Struct(Schema):
  """
  <Purpose>
    Matches a non-homogeneous list of items.  The sub-schemas are allowed to
    vary.  The object argument must be a sequence type (e.g., a list, tuple,
    etc.).  There is also an option to specify that additional schemas not
    explicitly defined at instantiation are allowed.  See __init__() for the
    complete list of arguments accepted.

    Supported methods include:
      matches(): returns a Boolean result.
      check_match(): raises 'exceptions.FormatError' on a mismatch.

  <Example Use>
    >>> schema = Struct([ListOf(AnyString()), AnyString(), String('X')])
    >>> schema.matches(False)
    False
    >>> schema.matches('Foo')
    False
    >>> schema.matches([[], 'Q', 'X'])
    True
    >>> schema.matches([[], 'Q', 'D'])
    False
    >>> schema.matches([[3], 'Q', 'X'])
    False
    >>> schema.matches([[], 'Q', 'X', 'Y'])
    False
    >>> schema = Struct([String('X')], allow_more=True)
    >>> schema.matches([])
    False
    >>> schema.matches(['X'])
    True
    >>> schema.matches(['X', 'Y'])
    True
    >>> schema.matches(['X', ['Y', 'Z']])
    True
    >>> schema.matches([['X']])
    False
    >>> schema = Struct([String('X'), Integer()], [Integer()])
    >>> schema.matches([])
    False
    >>> schema.matches({})
    False
    >>> schema.matches(['X'])
    False
    >>> schema.matches(['X', 3])
    True
    >>> schema.matches(['X', 3, 9])
    True
    >>> schema.matches(['X', 3, 9, 11])
    False
    >>> schema.matches(['X', 3, 'A'])
    False
  """

  def __init__(self, sub_schemas, optional_schemas=[], allow_more=False,
               struct_name='list'):
    """
    <Purpose>
      Create a new Struct schema.

    <Arguments>
      sub_schemas: The sub-schemas recognized.
      optional_schemas: The optional list of schemas.
      allow_more: Specifies that an optional list of types is allowed.
      struct_name: A string identifier for the Struct object.
    """

    # Ensure each item of the list contains the expected object type.
    if not isinstance(sub_schemas, (list, tuple)):
      raise securesystemslib.exceptions.FormatError(
          'Expected Schema but got ' + repr(sub_schemas))

    for schema in sub_schemas:
      if not isinstance(schema, Schema):
        raise securesystemslib.exceptions.FormatError('Expected Schema but'
            ' got ' + repr(schema))

    self._sub_schemas = sub_schemas + optional_schemas
    self._min = len(sub_schemas)
    self._allow_more = allow_more
    self._struct_name = struct_name


  def check_match(self, object):
    if not isinstance(object, (list, tuple)):
      raise securesystemslib.exceptions.FormatError(
          'Expected ' + repr(self._struct_name) + '; but got ' + repr(object))

    elif len(object) < self._min:
      raise securesystemslib.exceptions.FormatError(
          'Too few fields in ' + self._struct_name)

    elif len(object) > len(self._sub_schemas) and not self._allow_more:
      raise securesystemslib.exceptions.FormatError(
          'Too many fields in ' + self._struct_name)

    # Iterate through the items of 'object', checking against each schema in
    # the list of schemas allowed (i.e., the sub-schemas and also any optional
    # schemas.  The lenth of 'object' must be less than the length of the
    # required schemas + the optional schemas.  However, 'object' is allowed to
    # be only as large as the length of the required schemas.  In the while
    # loop below, we check against these two cases.
    index = 0
    while index < len(object) and index < len(self._sub_schemas):
      item = object[index]
      schema = self._sub_schemas[index]
      schema.check_match(item)
      index = index + 1





class RegularExpression(Schema):
  """
  <Purpose>
    Matches any string that matches a given regular expression.  The RE pattern
    set when RegularExpression is instantiated must not be None.  See
    __init__() for a complete list of accepted arguments.

    Supported methods include:
      matches(): returns a Boolean result.
      check_match(): raises 'exceptions.FormatError' on a mismatch.

  <Example Use>
    >>> schema = RegularExpression('h.*d')
    >>> schema.matches('hello world')
    True
    >>> schema.matches('Hello World')
    False
    >>> schema.matches('hello world!')
    False
    >>> schema.matches([33, 'Hello'])
    False
  """

  def __init__(self, pattern=None, modifiers=0, re_object=None, re_name=None):
    """
    <Purpose>
      Create a new regular expression schema.

    <Arguments>
      pattern:  The pattern to match, or None if re_object is provided.
      modifiers:  Flags to use when compiling the pattern.
      re_object:  A compiled regular expression object.
      re_name: Identifier for the regular expression object.
    """

    if not isinstance(pattern, six.string_types):
      if pattern is not None:
        raise securesystemslib.exceptions.FormatError(
            repr(pattern) + ' is not a string.')

    if re_object is None:
      if pattern is None:
        raise securesystemslib.exceptions.FormatError(
            'Cannot compare against an unset regular expression')

      if not pattern.endswith('$'):
        pattern += '$'
      re_object = re.compile(pattern, modifiers)
    self._re_object = re_object

    if re_name is None:
      if pattern is not None:
        re_name = 'pattern /' + pattern + '/'

      else:
        re_name = 'pattern'
    self._re_name = re_name


  def check_match(self, object):
    if not isinstance(object, six.string_types) or not self._re_object.match(object):
      raise securesystemslib.exceptions.FormatError(
          repr(object) + ' did not match ' + repr(self._re_name))



if __name__ == '__main__':
  # The interactive sessions of the documentation strings can
  # be tested by running schema.py as a standalone module.
  # python -B schema.py.
  import doctest
  doctest.testmod()


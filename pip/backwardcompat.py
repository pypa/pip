"""Stuff that differs in different Python versions"""

import sys
import os
import shutil
import base64

__all__ = ['any', 'WindowsError', 'md5', 'copytree']

try:
    WindowsError = WindowsError
except NameError:
    class NeverUsedException(Exception):
        """this exception should never be raised"""
    WindowsError = NeverUsedException
try:
    from hashlib import md5
except ImportError:
    import md5 as md5_module
    md5 = md5_module.new

try:
    from pkgutil import walk_packages
except ImportError:
    # let's fall back as long as we can
    from pip._pkgutil import walk_packages

try:
    any = any
except NameError:

    def any(seq):
        for item in seq:
            if item:
                return True
        return False

console_encoding = sys.__stdout__.encoding

if sys.version_info >= (3,):
    from io import StringIO, BytesIO
    from functools import reduce
    from urllib.error import URLError, HTTPError
    from queue import Queue, Empty
    from urllib.request import url2pathname
    from urllib.request import urlretrieve
    from email import message as emailmessage
    import urllib.parse as urllib
    import urllib.request as urllib2
    import configparser as ConfigParser
    import xmlrpc.client as xmlrpclib
    import urllib.parse as urlparse
    import http.client as httplib

    def cmp(a, b):
        return (a > b) - (a < b)

    def b(s):
        return s.encode('utf-8')

    def u(s):
        return s.decode('utf-8')

    def _ord(x):
        return x

    def console_to_str(s):
        return s.decode(console_encoding)
    bytes = bytes
    string_types = (str,)
    raw_input = input

    def decode_base64(source):
        source = source.encode("ascii")  # ensure bytes
        return base64.decodebytes(source)

    _long = lambda x: x

else:
    from cStringIO import StringIO
    from urllib2 import URLError, HTTPError
    from Queue import Queue, Empty
    from urllib import url2pathname, urlretrieve
    from email import Message as emailmessage
    import urllib
    import urllib2
    import urlparse
    import ConfigParser
    import xmlrpclib
    import httplib

    def b(s):
        return s

    def u(s):
        return s

    def _ord(x):
        return ord(x)

    def console_to_str(s):
        return s
    bytes = str
    string_types = (basestring,)
    reduce = reduce
    cmp = cmp
    raw_input = raw_input
    BytesIO = StringIO
    decode_base64 = base64.decodestring
    _long = lambda x: long(x)

try:
    from email.parser import FeedParser
except ImportError:
    # python lesser than 2.5
    from email.FeedParser import FeedParser

from distutils.sysconfig import get_python_lib, get_python_version


def copytree(src, dst):
    if sys.version_info < (2, 5):
        before_last_dir = os.path.dirname(dst)
        if not os.path.exists(before_last_dir):
            os.makedirs(before_last_dir)
        shutil.copytree(src, dst)
        shutil.copymode(src, dst)
    else:
        shutil.copytree(src, dst)


def product(*args, **kwds):
    # product('ABCD', 'xy') --> Ax Ay Bx By Cx Cy Dx Dy
    # product(range(2), repeat=3) --> 000 001 010 011 100 101 110 111
    pools = list(map(tuple, args)) * kwds.get('repeat', 1)
    result = [[]]
    for pool in pools:
        result = [x+[y] for x in result for y in pool]
    for prod in result:
        yield tuple(prod)

try:
    from collections import OrderedDict
except ImportError:
    # Copyright (c) 2009 Raymond Hettinger
    #
    # Permission is hereby granted, free of charge, to any person
    # obtaining a copy of this software and associated documentation files
    # (the "Software"), to deal in the Software without restriction,
    # including without limitation the rights to use, copy, modify, merge,
    # publish, distribute, sublicense, and/or sell copies of the Software,
    # and to permit persons to whom the Software is furnished to do so,
    # subject to the following conditions:
    #
    #     The above copyright notice and this permission notice shall be
    #     included in all copies or substantial portions of the Software.
    #
    #     THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
    #     EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
    #     OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
    #     NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
    #     HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
    #     WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
    #     FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
    #     OTHER DEALINGS IN THE SOFTWARE.
    from UserDict import DictMixin

    class OrderedDict(dict, DictMixin):

        def __init__(self, *args, **kwds):
            if len(args) > 1:
                raise TypeError('expected at most 1 arguments, got %d' % len(args))
            try:
                self.__end
            except AttributeError:
                self.clear()
            self.update(*args, **kwds)

        def clear(self):
            self.__end = end = []
            end += [None, end, end]         # sentinel node for doubly linked list
            self.__map = {}                 # key --> [key, prev, next]
            dict.clear(self)

        def __setitem__(self, key, value):
            if key not in self:
                end = self.__end
                curr = end[1]
                curr[2] = end[1] = self.__map[key] = [key, curr, end]
            dict.__setitem__(self, key, value)

        def __delitem__(self, key):
            dict.__delitem__(self, key)
            key, prev, next = self.__map.pop(key)
            prev[2] = next
            next[1] = prev

        def __iter__(self):
            end = self.__end
            curr = end[2]
            while curr is not end:
                yield curr[0]
                curr = curr[2]

        def __reversed__(self):
            end = self.__end
            curr = end[1]
            while curr is not end:
                yield curr[0]
                curr = curr[1]

        def popitem(self, last=True):
            if not self:
                raise KeyError('dictionary is empty')
            if last:
                key = reversed(self).next()
            else:
                key = iter(self).next()
            value = self.pop(key)
            return key, value

        def __reduce__(self):
            items = [[k, self[k]] for k in self]
            tmp = self.__map, self.__end
            del self.__map, self.__end
            inst_dict = vars(self).copy()
            self.__map, self.__end = tmp
            if inst_dict:
                return (self.__class__, (items,), inst_dict)
            return self.__class__, (items,)

        def keys(self):
            return list(self)

        setdefault = DictMixin.setdefault
        update = DictMixin.update
        pop = DictMixin.pop
        values = DictMixin.values
        items = DictMixin.items
        iterkeys = DictMixin.iterkeys
        itervalues = DictMixin.itervalues
        iteritems = DictMixin.iteritems

        def __repr__(self):
            if not self:
                return '%s()' % (self.__class__.__name__,)
            return '%s(%r)' % (self.__class__.__name__, self.items())

        def copy(self):
            return self.__class__(self)

        @classmethod
        def fromkeys(cls, iterable, value=None):
            d = cls()
            for key in iterable:
                d[key] = value
            return d

        def __eq__(self, other):
            if isinstance(other, OrderedDict):
                if len(self) != len(other):
                    return False
                for p, q in  zip(self.items(), other.items()):
                    if p != q:
                        return False
                return True
            return dict.__eq__(self, other)

        def __ne__(self, other):
            return not self == other


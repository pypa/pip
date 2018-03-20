# -*- coding: utf-8 -*-
"""
serializer error tests

"""
from __future__ import unicode_literals
import unittest

from mock import Mock, patch
from pip._vendor.cachecontrol.serialize import Serializer


class Tests_Serializer(unittest.TestCase):
    "Test handling of cache loading errors"

    serializer = Serializer()
    mock_request = Mock(headers={})

    @patch('pip._vendor.cachecontrol.serialize.pickle')
    def test_serializer_import_error_returns(self, mock_pickle):
        mock_pickle.loads.side_effect = ImportError()
        self.assertIs(
            self.serializer._loads_v1(self.mock_request, b'data'),
            None)

    @patch('pip._vendor.cachecontrol.serialize.pickle')
    def test_serializer_value_error_returns(self, mock_pickle):
        mock_pickle.loads.side_effect = ValueError()
        self.assertIs(
            self.serializer._loads_v1(self.mock_request, b'data'),
            None)

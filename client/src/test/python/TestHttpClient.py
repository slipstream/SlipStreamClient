#!/usr/bin/env python
"""
 SlipStream Client
 =====
 Copyright (C) 2013 SixSq Sarl (sixsq.com)
 =====
 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at

      http://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
"""

import httplib2
import unittest
import tempfile
import shutil

from mock import Mock

from slipstream.HttpClient import HttpClient
from slipstream.exceptions.Exceptions import NetworkError


class HttpClientTestCase(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testGetWithUsernamePassword(self):

        httpRequestMock = Mock(return_value=(httplib2.Response({}), ''))

        httpObjectMock = Mock()
        httpObjectMock.request = httpRequestMock

        mock = Mock(return_value=httpObjectMock)
        HttpClient._getHttpObject = mock

        client = HttpClient('username', 'password')
        client.get('url')

        args, kwargs = httpRequestMock.call_args

        self.assertEqual(('url', 'GET', None), args)

        self.assertTrue(kwargs['headers']['Authorization'].startswith('Basic '))

    def testGetSetsCookie(self):

        # Use an alternate temporary directory to avoid conflicts in file
        # permissions on /tmp/slipstream/cookie if different users run the
        # tests on the same machine.
        temp_dir = tempfile.mkdtemp()
        try:
            tempfile.tempdir = temp_dir

            httpRequestMock = Mock(return_value=(httplib2.Response({'set-cookie': 'acookie'}), ''))

            httpObjectMock = Mock()
            httpObjectMock.request = httpRequestMock

            mock = Mock(return_value=httpObjectMock)
            HttpClient._getHttpObject = mock

            client = HttpClient('username', 'password')
            client.get('http://localhost:9999/url')

            self.assertEqual('acookie', client.cookie)

        finally:
            tempfile.tempdir = None
            shutil.rmtree(temp_dir)

    def testGetWithCookie(self):

        httpRequestMock = Mock(return_value=(httplib2.Response({}), ''))

        httpObjectMock = Mock()
        httpObjectMock.request = httpRequestMock

        mock = Mock(return_value=httpObjectMock)
        HttpClient._getHttpObject = mock

        client = HttpClient()
        client.cookie = 'acookie'

        client.get('url')

        _, kwargs = httpRequestMock.call_args

        headers = kwargs['headers']
        self.assertEqual(headers['cookie'], 'acookie')

    def testUnknownHttpReturnCode(self):

        httpRequestMock = Mock(return_value=(httplib2.Response({'status': '999'}), ''))

        httpObjectMock = Mock()
        httpObjectMock.request = httpRequestMock

        mock = Mock(return_value=httpObjectMock)
        HttpClient._getHttpObject = mock

        client = HttpClient('username', 'password')
        client.cookie = 'acookie'

        self.assertRaises(NetworkError, client.get, 'url')

    def testBasicAuthenticationHeaderSet(self):

        client = HttpClient('username', 'password')
        headers = client._createAuthenticationHeader()

        self.assertTrue(headers['Authorization'].startswith('Basic '))

    def testCookieHeaderSet(self):

        client = HttpClient(cookie='acookie')
        headers = client._createAuthenticationHeader()

        self.assertEqual('acookie', headers['cookie'])


if __name__ == '__main__':
    unittest.main()

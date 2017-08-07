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

import cookielib
import requests
import unittest

from mock import Mock
from requests.cookies import RequestsCookieJar

from slipstream.HttpClient import HttpClient
from slipstream.exceptions.Exceptions import NetworkError


class HttpClientTestCase(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_get_with_username_password(self):

        client = HttpClient('username', 'password')
        client.verboseLevel = 0
        client.session = Mock()
        client.session.cookies = []
        resp = Mock(spec_set=requests.Response())
        resp.request = Mock()
        resp.request.headers = {}
        resp.status_code = 200
        client.session.request = Mock(return_value=resp)

        client.get('http://foo.bar', retry=False)

        args, kwargs = client.session.request.call_args
        self.assertEqual(('GET', 'http://foo.bar'), args)
        self.assertTrue(kwargs['auth'], ('username', 'password'))

    def test_get_with_oldstyle_cookie_string(self):

        client = HttpClient()
        client.verboseLevel = 0
        client.cookie = 'acookie=foo=bar'
        client.cookie_filename = '/dev/null'

        client.init_session('http://foo.bar')

        jar = RequestsCookieJar()
        jar.update(client.session.cookies)
        cookies = jar.get_dict(domain='foo.bar', path='/')
        self.assertEqual(1, len(cookies))
        self.assertEqual(cookies['acookie'], 'foo=bar')

    def test_unknown_http_return_code(self):

        client = HttpClient('username', 'password')
        client.verboseLevel = 0
        client.session = Mock()
        client.session.cookies = []
        resp = Mock(spec_set=requests.Response())
        resp.request = Mock()
        resp.request.headers = {}
        resp.status_code = 999
        client.session.request = Mock(return_value=resp)

        self.assertRaises(NetworkError, client.get, 'http://foo.bar',
                          retry=False)

    def test_post_with_data(self):
        client = HttpClient('username', 'password')
        client.verboseLevel = 0
        resp = requests.Response()
        resp.status_code = 200
        resp.get = Mock(return_value=None)
        resp.request = Mock()
        resp.request.headers = {}
        requests.sessions.Session.send = Mock(return_value=resp)

        client.post('http://example.com', 'a=b\nc=d')

        args, kwargs = requests.sessions.Session.send.call_args
        self.assertEqual(len(args), 1)
        req = args[0]
        self.assertEqual(req.body, 'a=b\nc=d')


if __name__ == '__main__':
    unittest.main()

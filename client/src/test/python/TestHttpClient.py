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

import requests
import unittest

from mock import Mock, call
from requests.cookies import RequestsCookieJar, create_cookie

from slipstream.HttpClient import HttpClient, get_cookie
from slipstream.exceptions.Exceptions import NetworkError
from slipstream.ConfigHolder import ConfigHolder
from slipstream.api.api import Api

Api.login_internal = Mock()
Api.login_apikey = Mock()


class HttpClientTestCase(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_init_session_fail_no_creds(self):
        ch = ConfigHolder()
        ch.set('verboseLevel', 0)
        ch.set('cookie_filename', '/dev/null')

        client = HttpClient(ch)

        self.assertRaisesRegexp(Exception, '^Unable to login',
                                client.init_session, ('http://foo.bar'))

    def test_init_session_success_login_internal(self):
        ch = ConfigHolder()
        ch.set('verboseLevel', 0)
        ch.set('cookie_filename', '/dev/null')
        ch.set('username', 'foo')
        ch.set('password', 'bar')

        client = HttpClient(ch)
        client.init_session('http://foo.bar')
        assert client.session is not None
        assert Api.login_internal.called is True
        assert Api.login_internal.call_args == call('foo', 'bar')

    def test_init_session_success_login_apikey(self):
        ch = ConfigHolder()
        ch.set('verboseLevel', 0)
        ch.set('cookie_filename', '/dev/null')
        ch.set('api_key', 'key')
        ch.set('api_secret', 'secret')

        client = HttpClient(ch)
        client.init_session('http://foo.bar')
        assert client.session is not None
        assert Api.login_apikey.called is True
        assert Api.login_apikey.call_args == call('key', 'secret')

    def test_unknown_http_return_code(self):
        client = HttpClient()
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
        ch = ConfigHolder()
        ch.set('verboseLevel', 0)
        ch.set('cookie_filename', '/dev/null')
        ch.set('api_key', 'key')
        ch.set('api_secret', 'secret')
        client = HttpClient(ch)
        resp = requests.Response()
        resp.status_code = 200
        resp.get = Mock(return_value=None)
        resp.request = Mock()
        resp.request.headers = {}
        requests.sessions.Session.send = Mock(return_value=resp)

        client.post('http://example.com', 'a=b\nc=d')

        assert Api.login_apikey.called is True
        assert Api.login_apikey.call_args == call('key', 'secret')

        args, kwargs = requests.sessions.Session.send.call_args
        self.assertEqual(len(args), 1)
        req = args[0]
        self.assertEqual(req.body, 'a=b\nc=d')

    def test_get_cookie(self):
        self.assertIsNone(get_cookie(RequestsCookieJar(), None))

        cookie_str = 'cookie.name=this is a cookie'
        name, value = cookie_str.split('=')
        domain = 'example.com'
        path = '/some'

        jar = RequestsCookieJar()
        cookie = create_cookie(name, value, **{'domain': domain, 'path': path})
        jar.set_cookie(cookie)

        # w/o path
        self.assertIsNone(get_cookie(jar, None))
        self.assertIsNone(get_cookie(jar, domain))
        c_str = get_cookie(jar, domain, name=name)
        self.assertIsNotNone(c_str)
        self.assertEquals(cookie_str, c_str)

        # w/ path
        self.assertIsNone(get_cookie(jar, domain, path='/', name=name))

        c_str = get_cookie(jar, domain, path='/some', name=name)
        self.assertEquals(cookie_str, c_str)

        c_str = get_cookie(jar, domain, path='/some/path', name=name)
        self.assertEquals(cookie_str, c_str)

        # root path cookie
        jar = RequestsCookieJar()
        cookie = create_cookie(name, value, **{'domain': domain, 'path': '/'})
        jar.set_cookie(cookie)
        c_str = get_cookie(jar, domain, path='/', name=name)
        self.assertEquals(cookie_str, c_str)

        c_str = get_cookie(jar, domain, path='/random', name=name)
        self.assertEquals(cookie_str, c_str)


if __name__ == '__main__':
    unittest.main()

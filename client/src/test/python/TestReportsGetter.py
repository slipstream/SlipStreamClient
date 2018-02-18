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

from requests.cookies import RequestsCookieJar, create_cookie

from slipstream.SlipStreamHttpClient import DEFAULT_SS_COOKIE_NAME
from slipstream.resources.reports import ReportsGetter, NO_SESSION_PROVIDED_MSG
from slipstream.ConfigHolder import ConfigHolder


class TestResultArchiver(unittest.TestCase):

    def test_session_not_provided(self):
        self.assertRaisesRegexp(Exception, NO_SESSION_PROVIDED_MSG,
                                ReportsGetter, ConfigHolder())

    def test_session_provided(self):
        ch = ConfigHolder()
        ch.set("session", requests.Session())
        rg = ReportsGetter(ch)
        self.assertIsInstance(rg.session, requests.Session)

    def test_cookie_obtained_from_session(self):
        # session with empty cookie jar
        ch = ConfigHolder()
        ch.set("session", requests.Session())
        rg = ReportsGetter(ch)
        self.assertIsNone(rg._get_cookie('http://example.com/', 'some.name'))

        # session with non empty cookie jar
        ch = ConfigHolder()
        session = requests.Session()
        jar = RequestsCookieJar()
        cvalue = 'this is a cookie'
        domain = 'example.com'
        cookie = create_cookie(DEFAULT_SS_COOKIE_NAME, cvalue,
                               **{'domain': domain,
                                  'path': '/reports'})
        jar.set_cookie(cookie)
        session.cookies = jar
        ch.set("session", session)
        rg = ReportsGetter(ch)
        self.assertEquals('%s=%s' % (DEFAULT_SS_COOKIE_NAME, cvalue),
                          rg._get_cookie('http://example.com/reports/uuid',
                                         DEFAULT_SS_COOKIE_NAME))


if __name__ == '__main__':
    unittest.main()

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

import unittest
import os
import shutil

from slipstream.Client import Client
from slipstream.resources.reports import ReportsGetter
from slipstream.ConfigHolder import ConfigHolder

# This is a live test and intended to be run manually. To run the test,
# 1. set the vars below;
# 2. 'run_uuid' should be uuid of a run with reports.
# NB: Don't commit the variables!!!
username = ''
password = ''
run_uuid = ''
endpoint = 'https://nuv.la'


class TestResultArchiver(unittest.TestCase):

    def setUp(self):
        self.ch = ConfigHolder()
        self.ch.set('serviceurl', endpoint)
        self.ch.set('verboseLevel', 3)

        self.client = Client(self.ch)
        self.client.login(username, password)
        self.ch.set('endpoint', endpoint)
        self.ch.set('session', self.client.get_session())

    def tearDown(self):
        shutil.rmtree(run_uuid, ignore_errors=True)
        try: self.client.logout()
        except: pass

    @unittest.skipIf(not all([username, password, run_uuid]),
                     "Live test. Creds not set.")
    def test_get_reports(self):
        rg = ReportsGetter(self.ch)
        rg.get_reports(run_uuid)
        self.assertTrue(os.path.isdir(run_uuid))


if __name__ == '__main__':
    unittest.main()

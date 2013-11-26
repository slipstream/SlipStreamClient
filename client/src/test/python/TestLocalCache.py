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

import os
import unittest

from slipstream.LocalCache import LocalCache


class LocalCacheTestCase(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testSetGet(self):

        if(os.path.exists(LocalCache.CACHE_FILENAME)):
            os.remove(LocalCache.CACHE_FILENAME)

        cache = LocalCache()

        cache.set('key', 'value')
        self.assertEquals('value', cache.get('key'))

        cache = LocalCache()
        self.assertEquals('value', cache.get('key'))


if __name__ == '__main__':
    unittest.main()

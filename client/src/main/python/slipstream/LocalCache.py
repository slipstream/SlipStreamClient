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
from ConfigParser import SafeConfigParser


class LocalCache(object):

    CACHE_FILENAME = '/tmp/slipstream.cache'
    SECTION = 'cache'

    def __init__(self):
        self.uuid = None
        self.category = None
        self.parser = None
        self._load()

    def _load(self):
        self.parser = self._getParser()

    def _getParser(self):
        parser = SafeConfigParser()
        if os.path.exists(LocalCache.CACHE_FILENAME):
            parser.read(LocalCache.CACHE_FILENAME)
        else:
            parser.add_section(LocalCache.SECTION)
        return parser

    def get(self, key):
        return self.parser.get(LocalCache.SECTION, key)

    def set(self, key, value):
        self.parser.set(LocalCache.SECTION, key, value)
        self._save()

    def _save(self):
        self.parser.write(open(LocalCache.CACHE_FILENAME, 'w'))

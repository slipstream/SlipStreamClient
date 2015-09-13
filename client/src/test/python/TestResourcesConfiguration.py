#!/usr/bin/env python
"""
 SlipStream Client
 =====
 Copyright (C) 2015 SixSq Sarl (sixsq.com)
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

from slipstream.resources.configuration import _connector_classes_str_to_dict
from slipstream.resources.configuration import get_cloud_connector_classes
from slipstream.util import SERVER_CONFIGURATION_BASICS_CATEGORY
from slipstream.util import SERVER_CONFIGURATION_CONNECTOR_CLASSES_KEY


class TestConfigurationResource(unittest.TestCase):

    def test_connector_classes_str_to_dict(self):
        assert {} == _connector_classes_str_to_dict('')
        assert {'foo': 'foo'} == _connector_classes_str_to_dict('foo')
        assert {'foo': 'bar'} == _connector_classes_str_to_dict('foo:bar')

        res = _connector_classes_str_to_dict('foo:bar, baz')
        unmatched_items = set([('foo', 'bar'), ('baz', 'baz')]) ^ set(res.items())
        assert 0 == len(unmatched_items)

    def test_get_cloud_connector_classes_from_basics_category(self):
        assert {} == get_cloud_connector_classes({})
        assert {} == get_cloud_connector_classes({'foo': 'bar'})
        assert {} == get_cloud_connector_classes({SERVER_CONFIGURATION_BASICS_CATEGORY: []})
        assert {} == get_cloud_connector_classes({SERVER_CONFIGURATION_BASICS_CATEGORY: [(),]})
        assert {} == get_cloud_connector_classes({SERVER_CONFIGURATION_BASICS_CATEGORY: [('',''),]})

        conf = {SERVER_CONFIGURATION_BASICS_CATEGORY: [(SERVER_CONFIGURATION_CONNECTOR_CLASSES_KEY, ''),]}
        assert {} == get_cloud_connector_classes(conf)

        conf = {SERVER_CONFIGURATION_BASICS_CATEGORY: [(SERVER_CONFIGURATION_CONNECTOR_CLASSES_KEY, 'foo'),]}
        assert {'foo': 'foo'} == get_cloud_connector_classes(conf)


if __name__ == '__main__':
    unittest.main()

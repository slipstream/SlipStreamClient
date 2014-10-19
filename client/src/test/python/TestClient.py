#!/usr/bin/env python
"""
 SlipStream Client
 =====
 Copyright (C) 2014 SixSq Sarl (sixsq.com)
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

from slipstream.Client import Client
from slipstream.NodeDecorator import NodeDecorator
from slipstream.ConfigHolder import ConfigHolder


class TestClient(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_do_not_qualify_parameter(self):
        orch_node_name = NodeDecorator.orchestratorName + '-cloudX'
        orch_param = orch_node_name + NodeDecorator.NODE_PROPERTY_SEPARATOR + 'foo'

        context = {NodeDecorator.NODE_INSTANCE_NAME_KEY: orch_node_name}
        ch = ConfigHolder(context=context, config={'bar': 'baz'})
        c = Client(ch)
        assert orch_param == c._qualifyKey(orch_param)


if __name__ == '__main__':
    unittest.main()

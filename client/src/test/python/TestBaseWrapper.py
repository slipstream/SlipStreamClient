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
import base64
import shutil
import os

from mock import Mock

from slipstream.ConfigHolder import ConfigHolder
from slipstream.NodeDecorator import NodeDecorator
from slipstream.NodeInstance import NodeInstance
from slipstream.util import ENV_CONNECTOR_INSTANCE
from slipstream.wrappers.BaseWrapper import BaseWrapper

from TestCloudConnectorsBase import TestCloudConnectorsBase


class TestBaseWrapper(TestCloudConnectorsBase):

    def setUp(self):
        self.serviceurl = 'http://example.com'
        self.config_holder = ConfigHolder(
            {
                'username': base64.b64encode('user'),
                'password': base64.b64encode('pass'),
                'cookie_filename': 'cookies',
                'serviceurl': self.serviceurl,
                'node_instance_name': 'instance-name'
            },
            context={'foo': 'bar'},
            config={'foo': 'bar'})

        os.environ[ENV_CONNECTOR_INSTANCE] = 'Test'

        BaseWrapper.is_mutable = Mock(return_value=False)

    def tearDown(self):
        os.environ.pop(ENV_CONNECTOR_INSTANCE)
        self.config_holder = None
        shutil.rmtree('%s/.cache/' % os.getcwd(), ignore_errors=True)

    def test_build_rtp(self):
        assert 'foo:bar' == BaseWrapper._build_rtp('foo', 'bar')
        node_instance = NodeInstance({NodeDecorator.NODE_INSTANCE_NAME_KEY: 'foo'})
        assert 'foo:bar' == BaseWrapper._build_rtp(node_instance, 'bar')

    def test_get_pre_scale_done(self):
        bw = BaseWrapper(self.config_holder)
        bw._get_runtime_parameter = Mock(return_value='true')
        node_instance = NodeInstance({NodeDecorator.NODE_INSTANCE_NAME_KEY: 'foo'})
        assert 'true' == bw.get_pre_scale_done(node_instance)
        assert bw._get_runtime_parameter.called_with('foo:' + NodeDecorator.PRE_SCALE_DONE)

        bw._get_runtime_parameter = Mock(return_value='')
        assert '' == bw.get_pre_scale_done('foo')
        assert bw._get_runtime_parameter.called_with('foo:' + NodeDecorator.PRE_SCALE_DONE)


if __name__ == "__main__":
    unittest.main()

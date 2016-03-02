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
import os

from mock import Mock

from slipstream.NodeDecorator import NodeDecorator
from slipstream.NodeInstance import NodeInstance
from slipstream.util import ENV_CONNECTOR_INSTANCE
from slipstream.cloudconnectors.BaseCloudConnector import BaseCloudConnector

from TestCloudConnectorsBase import TestCloudConnectorsBase


class TestBaseWrapper(TestCloudConnectorsBase):
    def setUp(self):
        os.environ[ENV_CONNECTOR_INSTANCE] = 'Test'

    def tearDown(self):
        os.environ.pop(ENV_CONNECTOR_INSTANCE)

    def test___create_allow_all_security_group_if_needed(self):
        bcc = BaseCloudConnector(self._getMockedConfigHolder())
        bcc._create_allow_all_security_group = Mock()

        nis = {'comp.1': NodeInstance({NodeDecorator.CLOUDSERVICE_KEY: 'cloud-x',
                                       'cloud-x.' + NodeDecorator.SECURITY_GROUPS_KEY: 'foo, bar'})}
        bcc._BaseCloudConnector__create_allow_all_security_group_if_needed(nis)
        assert not bcc._create_allow_all_security_group.called

        nis.update({'comp.2': NodeInstance({NodeDecorator.CLOUDSERVICE_KEY: 'cloud-x',
                                            'cloud-x.' + NodeDecorator.SECURITY_GROUPS_KEY:
                                                'foo, ' + NodeDecorator.SECURITY_GROUP_ALLOW_ALL_NAME})})
        bcc._BaseCloudConnector__create_allow_all_security_group_if_needed(nis)
        assert bcc._create_allow_all_security_group.called


if __name__ == "__main__":
    unittest.main()

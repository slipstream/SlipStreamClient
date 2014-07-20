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

import os

from slipstream.cloudconnectors.CloudConnectorFactory import CloudConnectorFactory
from slipstream.cloudconnectors.BaseCloudConnector import BaseCloudConnector
from slipstream.util import CONFIGPARAM_CONNECTOR_MODULE_NAME

from TestCloudConnectorsBase import TestCloudConnectorsBase


class TestCloudConnectors(TestCloudConnectorsBase):

    os.environ['SLIPSTREAM_CONNECTOR_INSTANCE'] = 'Test'

    def setUp(self):
        self.ch = self._getMockedConfigHolder()

    def tearDown(self):
        self.ch = None

    def test_loadCloudConectors(self):
        for module_name in self.get_cloudconnector_modulenames():
            setattr(self.ch, CONFIGPARAM_CONNECTOR_MODULE_NAME, module_name)
            cc = CloudConnectorFactory.createConnector(self.ch)
            assert isinstance(cc, BaseCloudConnector)
            assert cc.get_cloud_service_name() == 'Test'

    def test_vmGetIdIpImplemented(self):
        for module_name in self.get_cloudconnector_modulenames():
            setattr(self.ch, CONFIGPARAM_CONNECTOR_MODULE_NAME, module_name)
            cc = CloudConnectorFactory.createConnector(self.ch)
            try:
                cc._vm_get_id(object)
            except NotImplementedError:
                self.fail('Connector %s: _vm_get_id should be implemented.' % module_name)
            except Exception:
                pass
            try:
                cc._vm_get_ip(object)
            except NotImplementedError:
                self.fail('Connector %s: _vm_get_ip should be implemented.' % module_name)
            except Exception:
                pass

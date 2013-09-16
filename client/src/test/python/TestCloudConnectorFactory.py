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

import slipstream.cloudconnectors.CloudConnectorFactory as ccf_module 
from slipstream.ConfigHolder import ConfigHolder
from slipstream.exceptions.Exceptions import NotFoundError
from TestCloudConnectorsBase import TestCloudConnectorsBase
from slipstream.util import CONFIGPARAM_CONNECTOR_MODULE_NAME

class TestCloudConnectorFactory(TestCloudConnectorsBase):

    def test_getAvailableCloudConnectorsModuleNames(self):
        ch = ConfigHolder(config={'foo':'bar'},
                          context={'foo':'bar'})
        for module_name in self.get_cloudconnector_modulenames():
            setattr(ch, CONFIGPARAM_CONNECTOR_MODULE_NAME, module_name)
            try:
                assert len(ccf_module.get_connector_module_name(ch)) != 0
            except NotFoundError:
                self.fail('Should not have raised NotFoundError')

    def test_getExternalCloudConnectorModuleName(self):
        ch = ConfigHolder(config={'foo':'bar'},
                          context={'foo':'bar'})
        ch.cloud = 'baz'
        self.failUnlessRaises(NotFoundError, 
                              ccf_module.get_connector_module_name, (ch))

        module_name = 'foo.bar.baz'
        ch = ConfigHolder(config={'cloudconnector':module_name},
                          context={'foo':'bar'})
        ch.cloud = 'baz'
        assert module_name == ccf_module.get_connector_module_name(ch)

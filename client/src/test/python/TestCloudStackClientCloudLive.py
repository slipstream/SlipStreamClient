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
import time
import unittest
from mock import Mock

from slipstream.cloudconnectors.BaseCloudConnector import BaseCloudConnector
from slipstream.cloudconnectors.cloudstack.CloudStackClientCloud import CloudStackClientCloud
from slipstream.ConfigHolder import ConfigHolder
from slipstream.SlipStreamHttpClient import UserInfo
from slipstream.NodeDecorator import (NodeDecorator, RUN_CATEGORY_IMAGE,
                                      RUN_CATEGORY_DEPLOYMENT, KEY_RUN_CATEGORY)
from slipstream import util

CONFIG_FILE = os.path.join(os.path.dirname(__file__),
                           'pyunit.credentials.properties')

# Example configuration file.
"""
[Test]
General.ssh.public.key = ssh-rsa ....
cloudstack.endpoint = https://api.exoscale.ch/compute
cloudstack.key = xxx
cloudstack.secret = yyy
cloudstack.zone = CH-GV2
cloudstack.template = 8c7e60ae-3a30-4031-a3e6-29832d85d7cb
cloudstack.instance.type = Micro
cloudstack.security.groups = default
cloudstack.max.iaas.workers = 2
"""


class TestCloudStackClientCloud(unittest.TestCase):
    def setUp(self):
        BaseCloudConnector.publishVmInfo = Mock()

        os.environ['SLIPSTREAM_CONNECTOR_INSTANCE'] = 'cloudstack'
        os.environ['SLIPSTREAM_BOOTSTRAP_BIN'] = 'http://example.com/bootstrap'
        os.environ['SLIPSTREAM_DIID'] = '00000000-0000-0000-0000-%s' % time.time()

        if not os.path.exists(CONFIG_FILE):
            raise Exception('Configuration file %s not found.' % CONFIG_FILE)

        self.ch = ConfigHolder(configFile=CONFIG_FILE, context={'foo': 'bar'})
        self.ch.set(KEY_RUN_CATEGORY, '')
        self.ch.set('verboseLevel', self.ch.config['General.verbosity'])

        self.client = CloudStackClientCloud(self.ch)

        self.user_info = UserInfo('cloudstack')
        self.user_info['cloudstack.endpoint'] = self.ch.config['cloudstack.endpoint']
        self.user_info['cloudstack.zone'] = self.ch.config['cloudstack.zone']
        self.user_info['cloudstack.username'] = self.ch.config['cloudstack.key']
        self.user_info['cloudstack.password'] = self.ch.config['cloudstack.secret']
        self.user_info['General.ssh.public.key'] = self.ch.config['General.ssh.public.key']

        image_id = self.ch.config['cloudstack.template']
        self.multiplicity = 4
        self.max_iaas_workers = self.ch.config.get('cloudstack.max.iaas.workers',
                                                   str(self.multiplicity))
        self.node_info = {
            'multiplicity': self.multiplicity,
            'nodename': 'test_node',
            'image': {
                'cloud_parameters': {
                    'cloudstack': {
                        'cloudstack.instance.type': self.ch.config['cloudstack.instance.type'],
                        'cloudstack.security.groups': self.ch.config['cloudstack.security.groups']
                     },
                    'Cloud': {'network': 'public'}
                },
                'attributes': {
                    'imageId': image_id,
                    'platform': 'Ubuntu'
                },
                'targets': {
                    'prerecipe':
"""#!/bin/sh
set -e
set -x

ls -l /tmp
dpkg -l | egrep "nano|lvm" || true
""",
                    'recipe':
"""#!/bin/sh
set -e
set -x

dpkg -l | egrep "nano|lvm" || true
lvs
""",
                    'packages': ['lvm2', 'nano']
                }
            },
        }

    def tearDown(self):
        os.environ.pop('SLIPSTREAM_CONNECTOR_INSTANCE')
        os.environ.pop('SLIPSTREAM_BOOTSTRAP_BIN')
        self.client = None
        self.ch = None

    def test_1_startStopImages(self):
        self.client._get_max_workers = Mock(return_value=self.max_iaas_workers)
        self.client.run_category = RUN_CATEGORY_DEPLOYMENT

        try:
            self.client.startNodesAndClients(self.user_info, [self.node_info])

            util.printAndFlush('Instances started')

            vms = self.client.getVms()
            assert len(vms) == self.multiplicity
        finally:
            self.client.stopDeployment()

    def xtest_2_buildImage(self):
        self.client.run_category = RUN_CATEGORY_IMAGE

        image_info = self.client._extractImageInfoFromNodeInfo(self.node_info)

        self.client.startImage(self.user_info, image_info)
        instancesDetails = self.client.getVmsDetails()

        assert instancesDetails
        assert instancesDetails[0][NodeDecorator.MACHINE_NAME]

        self.client.buildImage(self.user_info, image_info)
        assert self.client.getNewImageId()


if __name__ == '__main__':
    unittest.main()

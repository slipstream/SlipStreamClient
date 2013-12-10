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
from mock import Mock

from slipstream.cloudconnectors.BaseCloudConnector import BaseCloudConnector
from slipstream.cloudconnectors.openstack.OpenStackClientCloud import OpenStackClientCloud
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
openstack.location = LVS
openstack.username = konstan@sixsq.com
openstack.password = xxx
openstack.imageid =  d02ee717-33f7-478b-ba14-02196978fea8
openstack.ssh.username = ubuntu
openstack.ssh.password = yyy
"""


class TestOpenStackClientCloud(unittest.TestCase):
    def setUp(self):
        BaseCloudConnector.publishVmInfo = Mock()

        os.environ['SLIPSTREAM_CONNECTOR_INSTANCE'] = 'openstack'
        os.environ['SLIPSTREAM_BOOTSTRAP_BIN'] = 'http://example.com/bootstrap'
        os.environ['SLIPSTREAM_DIID'] = '00000000-0000-0000-0000-000000000000'

        if not os.path.exists(CONFIG_FILE):
            raise Exception('Configuration file %s not found.' % CONFIG_FILE)

        self.ch = ConfigHolder(configFile=CONFIG_FILE, context={'foo': 'bar'})
        self.ch.set(KEY_RUN_CATEGORY, '')

        os.environ['OPENSTACK_SERVICE_TYPE'] = self.ch.config['OPENSTACK_SERVICE_TYPE']
        os.environ['OPENSTACK_SERVICE_NAME'] = self.ch.config['OPENSTACK_SERVICE_NAME']
        os.environ['OPENSTACK_SERVICE_REGION'] = self.ch.config['OPENSTACK_SERVICE_REGION']

        self.client = OpenStackClientCloud(self.ch)

        self.user_info = UserInfo('openstack')
        self.user_info['openstack.endpoint'] = self.ch.config['openstack.endpoint']
        self.user_info['openstack.tenant.name'] = self.ch.config['openstack.tenant.name']
        self.user_info['openstack.username'] = self.ch.config['openstack.username']
        self.user_info['openstack.password'] = self.ch.config['openstack.password']
        self.user_info['General.ssh.public.key'] = self.ch.config['General.ssh.public.key']

        security_groups = self.ch.config['openstack.security.groups']
        image_id = self.ch.config['openstack.imageid']
        self.multiplicity = 2
        self.node_info = {
            'multiplicity': self.multiplicity,
            'nodename': 'test_node',
            'image': {
                'cloud_parameters': {
                    'openstack': {
                        'openstack.instance.type': 'm1.tiny',
                        'openstack.security.groups': security_groups
                    },
                    'Cloud': {'network': 'private'}
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
                    'packages' : ['lvm2','nano']
                }
            },
        }

    def tearDown(self):
        os.environ.pop('SLIPSTREAM_CONNECTOR_INSTANCE')
        os.environ.pop('SLIPSTREAM_BOOTSTRAP_BIN')
        self.client = None
        self.ch = None

    def xtest_1_startStopImages(self):
        self.client.run_category = RUN_CATEGORY_DEPLOYMENT

        self.client.startNodesAndClients(self.user_info, [self.node_info])

        util.printAndFlush('Instances started')

        vms = self.client.getVms()
        assert len(vms) == self.multiplicity

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

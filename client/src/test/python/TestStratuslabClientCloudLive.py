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

from slipstream.cloudconnectors.stratuslab.StratuslabClientCloud import StratuslabClientCloud
from slipstream.ConfigHolder import ConfigHolder
from slipstream.SlipStreamHttpClient import UserInfo
from slipstream import util

CONFIG_FILE = os.path.join(os.path.dirname(__file__),
                           'pyunit.credentials.properties')
# Example configuration file.
"""
[Test]
stratuslab.username = konstan@sixsq.com
stratuslab.password = xxx
stratuslab.imageid =  HZTKYZgX7XzSokCHMB60lS0wsiv
"""


class TestStratusLabClientCloud(unittest.TestCase):
    def setUp(self):

        os.environ['SLIPSTREAM_CONNECTOR_INSTANCE'] = 'stratuslab'
        os.environ['SLIPSTREAM_BOOTSTRAP_BIN'] = 'http://example.com/bootstrap'
        os.environ['SLIPSTREAM_DIID'] = '00000000-0000-0000-0000-000000000000'

        if not os.path.exists(CONFIG_FILE):
            raise Exception('Configuration file %s not found.' % CONFIG_FILE)

        self.ch = ConfigHolder(configFile=CONFIG_FILE, context={'foo': 'bar'})
        self.ch.set('verboseLevel', self.ch.config['General.verbosity'])

        os.environ['SLIPSTREAM_MESSAGING_ENDPOINT'] = self.ch.config['SLIPSTREAM_MESSAGING_ENDPOINT']
        os.environ['SLIPSTREAM_MESSAGING_TYPE'] = self.ch.config['SLIPSTREAM_MESSAGING_TYPE']
        os.environ['SLIPSTREAM_MESSAGING_QUEUE'] = self.ch.config['SLIPSTREAM_MESSAGING_QUEUE']

        self.client = StratuslabClientCloud(self.ch)
        self.client._publish_vm_info = Mock()

        self.user_info = UserInfo('stratuslab')
        self.user_info['stratuslab.endpoint'] = self.ch.config['stratuslab.endpoint']
        self.user_info['stratuslab.ip.type'] = self.ch.config['stratuslab.ip.type']
        self.user_info['stratuslab.marketplace.endpoint'] = self.ch.config['stratuslab.marketplace.endpoint']
        self.user_info['stratuslab.password'] = self.ch.config['stratuslab.password']
        self.user_info['General.ssh.public.key'] = self.ch.config['General.ssh.public.key']
        self.user_info['stratuslab.username'] = self.ch.config['stratuslab.username']
        self.user_info['User.firstName'] = 'Foo'
        self.user_info['User.lastName'] = 'Bar'
        self.user_info['User.email'] = 'dont@bother.me'

        extra_disk_volatile = self.ch.config['stratuslab.extra.disk.volatile']
        image_id = self.ch.config['stratuslab.imageid']
        self.multiplicity = self.ch.config['stratuslab.multiplicity']
        self.max_iaas_workers = self.ch.config['stratuslab.max.iaas.workers']
        self.node_info = {
            'multiplicity': self.multiplicity,
            'nodename': 'test_node',
            'image': {
                'extra_disks': {},
                'cloud_parameters': {
                    'stratuslab': {
                        'stratuslab.instance.type': 'm1.small',
                        'stratuslab.disks.bus.type': 'virtio',
                        'stratuslab.cpu': '',
                        'stratuslab.ram': ''
                    },
                    'Cloud': {
                        'network': 'public',
                        'extra.disk.volatile': extra_disk_volatile
                    }
                },
                'attributes': {
                    'resourceUri': '',
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

    def xtest_1_startStopImages(self):

        self.client._get_max_workers = Mock(return_value=self.max_iaas_workers)

        try:
            self.client.startNodesAndClients(self.user_info, [self.node_info])

            util.printAndFlush('Instances started\n')

            vms = self.client.get_vms()
            assert len(vms) == int(self.multiplicity)
        finally:
            self.client._stop_deployment()

    def xtest_2_buildImage(self):
        image_info = self.client._extractImageInfoFromNodeInfo(self.node_info)
        self.client._prepareMachineForBuildImage = Mock()
        self.client.build_image(self.user_info, image_info)
        # StratusLab doesn't provide us with image ID
        assert '' == self.client.getNewImageId()

if __name__ == '__main__':
    unittest.main()

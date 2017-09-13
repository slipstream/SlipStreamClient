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
from __future__ import print_function

import sys

from slipstream.cloudconnectors.BaseCloudConnector import BaseCloudConnector


def getConnector(configHolder):
    return getConnectorClass()(configHolder)


def getConnectorClass():
    return DummyClientCloud


class DummyClientCloud(BaseCloudConnector):
    cloudName = 'local'

    def __init__(self, config_holder):
        super(DummyClientCloud, self).__init__(config_holder)

    def _build_image(self, user_info, node_instance):
        print('Building image. Dummy implementation.')
        print('for: ', user_info)
        print('with: ', node_instance)

    def _start_image(self, user_info, node_instance, vm_name):
        print('Starting image. Dummy implementation.')
        print('for: ', user_info)
        print('with: ', node_instance, vm_name)

    def _stop_vms_by_ids(self, ids):
        print('Stopping VM(s). Dummy implementation.')
        print('VM id(s):', ids)

    def _resize(self, node_instance):
        print('Resizing VM. Dummy implementation.')
        print('Node Instance:', node_instance)

    def _attach_disk(self, node_instance):
        print('Attaching disk to VM. Dummy implementation.')
        print('Node Instance:', node_instance)
        return 'foo'

    def _detach_disk(self, node_instance):
        print('Detaching disk from VM. Dummy implementation.')
        print('Node Instance:', node_instance)

    def getInstanceInfos(self):
        return {'node1.1:instanceid': 'id1', 'node1.1:hostname': 'ip1',
                'node2.1:instanceid': 'id2', 'node2.1:hostname': 'ip2'}

    def getNewImageId(self):
        return '1234abcd'

    def _vm_get_id(self, vm_instance):
        return 'id1'

    def _vm_get_ip(self, vm_instance):
        return 'ip1'

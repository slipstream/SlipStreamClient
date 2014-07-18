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

from slipstream.cloudconnectors.BaseCloudConnector import BaseCloudConnector


def getConnector(configHolder):
    return getConnectorClass()(configHolder)


def getConnectorClass():
    return DummyClientCloud


class DummyClientCloud(BaseCloudConnector):
    cloudName = 'local'

    def __init__(self, configHolder):
        super(DummyClientCloud, self).__init__(configHolder)

    def buildImage(self, userInfo, imageInfo):
        print 'Building image. Dummy implementation.'
        print 'for: ', userInfo
        print 'with: ', imageInfo

    def getInstanceInfos(self):
        return {'node1.1:instanceid': 'id1', 'node1.1:hostname': 'ip1',
                'node2.1:instanceid': 'id2', 'node2.1:hostname': 'ip2'}

    def getNewImageId(self):
        return '1234abcd'

    def _vm_get_id(self):
        return 'id1'

    def _vm_get_ip(self):
        return 'ip1'

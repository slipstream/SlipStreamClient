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

import base64
import json
import os
import unittest
import socket
from mock import Mock

from slipstream.cloudconnectors.stratuslab.StratuslabClientCloud import StratuslabClientCloud
from slipstream.ConfigHolder import ConfigHolder as SlipstreamConfigHolder
from slipstream.exceptions import Exceptions

from stratuslab.ConfigHolder import ConfigHolder as StratusLabConfigHolder
from stratuslab.Runner import Runner

class TestStratusLabClientCloud(unittest.TestCase):
    
    def setUp(self):
        os.environ['SLIPSTREAM_CONNECTOR_INSTANCE'] = 'stratuslab'

    def tearDown(self):
        os.environ.pop('SLIPSTREAM_CONNECTOR_INSTANCE')

    def test__getCreateImageMessagingMessage(self):

        msg = StratuslabClientCloud._getCreateImageMessagingMessage('/foo/bar')
        
        assert {'uri':'/foo/bar', 'imageid':''} == json.loads(base64.b64decode(msg))
        
    def test__getCreateImageTemplateMessaging(self):
        # no messaging type set
        imageInfo = {'attributes': {'resourceUri':''}}
        assert {} == StratuslabClientCloud._getCreateImageTemplateMessaging(imageInfo)
        
        resourceUri = '/resource/uri'
        imageInfo = {'attributes': {'resourceUri':resourceUri}}

        # AmazonSQS
        os.environ['SLIPSTREAM_MESSAGING_TYPE'] = 'amazonsqs'
        os.environ['SLIPSTREAM_MESSAGING_ENDPOINT'] = 'http://amazon.com'
        os.environ['SLIPSTREAM_MESSAGING_QUEUE'] = '/123/queue'
        tmpl = StratuslabClientCloud._getCreateImageTemplateMessaging(imageInfo)
        assert tmpl['MSG_TYPE'] == 'amazonsqs'
        assert tmpl['MSG_ENDPOINT'] == 'http://amazon.com'
        assert tmpl['MSG_QUEUE'] == '/123/queue'
        assert resourceUri + '/stratuslab' == json.loads(base64.b64decode(tmpl['MSG_MESSAGE']))['uri']

        # REST
        os.environ['SLIPSTREAM_MESSAGING_TYPE'] = 'rest'
        os.environ['SLIPSTREAM_MESSAGING_ENDPOINT'] = 'http://slipstream.sixsq.com'
        os.environ['SLIPSTREAM_MESSAGING_QUEUE'] = '/123/queue'
        tmpl = StratuslabClientCloud._getCreateImageTemplateMessaging(imageInfo)
        assert tmpl['MSG_TYPE'] == 'rest'
        assert tmpl['MSG_ENDPOINT'] == 'http://slipstream.sixsq.com'
        assert tmpl['MSG_QUEUE'] == resourceUri + '/stratuslab'
        
    def test_runInstanceMaxAttempts(self):
        stratuslabClient = StratuslabClientCloud(SlipstreamConfigHolder(context={'foo':'bar'},
                                                                        config={'foo':'bar'}))
        stratuslabClient.RUNINSTANCE_RETRY_TIMEOUT = 0
        stratuslabClient._doRunInstance = Mock()
        stratuslabClient._doRunInstance.side_effect = socket.error()

        self.failUnlessRaises(Exceptions.ExecutionException,
                              stratuslabClient._runInstance, 
                              *('abc', StratusLabConfigHolder()), max_attempts=5)
        assert stratuslabClient._doRunInstance.call_count == 5
        stratuslabClient._doRunInstance.call_count = 0

        self.failUnlessRaises(Exceptions.ExecutionException,
                              stratuslabClient._runInstance, 
                              *('abc', StratusLabConfigHolder()), max_attempts=0)
        assert stratuslabClient._doRunInstance.call_count == 1

    def test_extraDisksOnStratusLabRunner(self):
        stratuslabClient = StratuslabClientCloud(SlipstreamConfigHolder(context={'foo':'bar'},
                                                                        config={'foo':'bar'}))
        slch = StratusLabConfigHolder()
        slch.set('username', 'foo')
        slch.set('password', 'bar')
        slch.set('endpoint', 'example.com')
        slch.set('verboseLevel', 0)
        node = {}
        node['extra_disks'] = {'extra.disk.volatile':'123', # GB
                               'extra_disk_persistent':'1-2-3',
                               'extra_disk_readonly':'ABC'}
        stratuslabClient._setExtraDisksOnConfigHolder(slch, node)
        Runner._checkPersistentDiskAvailable = Mock()
        runner = stratuslabClient._getStratusLabRunner('abc', slch)
        assert runner.extraDiskSize == int('123') * 1024 # MB
        assert runner.persistentDiskUUID == '1-2-3'
        assert runner.readonlyDiskId == 'ABC'

if __name__ == '__main__':
    unittest.main()

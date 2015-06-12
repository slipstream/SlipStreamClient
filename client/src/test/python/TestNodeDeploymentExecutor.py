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
from mock import Mock

from slipstream.contextualizers.ContextualizerFactory import ContextualizerFactory
from slipstream.ConfigHolder import ConfigHolder
ContextualizerFactory.getContextAsDict = Mock(return_value={'foo':'bar'})
ConfigHolder._getConfigFromFileAsDict = Mock(return_value={'foo':'bar'})

from slipstream.NodeInstance import NodeInstance
from slipstream.executors.node.NodeDeploymentExecutor import NodeDeploymentExecutor
from slipstream.exceptions.Exceptions import AbortException
from TestCloudConnectorsBase import TestCloudConnectorsBase


class TestNodeDeploymentExecutor(TestCloudConnectorsBase):

    def setUp(self):
        self.ch = ConfigHolder(config={'foo':'bar'})

    def tearDown(self):
        self.ch = None

    def test_launch_target_script_bad_exec_format(self):
        wrapper = Mock()
        wrapper.fail = Mock()
        wrapper.isAbort = Mock(return_value=False)
        nde = NodeDeploymentExecutor(wrapper, config_holder=self.ch)
        target = 'foo'
        nde.node_instance = NodeInstance()
        nde.node_instance.set_image_targets({target: 'oops'})
        self.assertRaises(OSError, nde._launch_target_script,
                          *(target, {}, True))
        assert 1 == nde.wrapper.fail.call_count

    def test_launch_target_script_failure(self):
        wrapper = Mock()
        wrapper.fail = Mock()
        wrapper.isAbort = Mock(return_value=False)
        nde = NodeDeploymentExecutor(wrapper, config_holder=self.ch)
        nde.TARGET_POLL_INTERVAL = 1
        target = 'foo'
        nde.node_instance = NodeInstance()
        nde.node_instance.set_image_targets({target: '#!/bin/bash \n/command/not/found\n'})
        self.assertRaises(AbortException, nde._launch_target_script,
                          *(target, {}, True))
        assert 1 == nde.wrapper.fail.call_count

    def test_execute_scale_action_target_gets_global_scale_action(self):
        wrapper = Mock()
        wrapper.get_scale_action = Mock(return_value=None)
        wrapper.get_global_scale_action = Mock(return_value=None)
        nde = NodeDeploymentExecutor(wrapper, configHolder=self.ch)
        nde._execute_scale_action_target()
        assert True == nde.wrapper.get_global_scale_action.called
        assert False == nde.wrapper.get_scale_action.called


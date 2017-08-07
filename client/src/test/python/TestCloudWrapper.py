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

import unittest
import base64
import shutil
import os

from mock import Mock
import time

from slipstream.ConfigHolder import ConfigHolder
from slipstream.exceptions.Exceptions import TimeoutException, \
    InconsistentScalingNodesError, InconsistentScaleStateError
from slipstream.wrappers.CloudWrapper import CloudWrapper
from slipstream.wrappers.BaseWrapper import BaseWrapper
from slipstream.util import CONFIGPARAM_CONNECTOR_MODULE_NAME, ENV_CONNECTOR_INSTANCE
from slipstream.NodeDecorator import NodeDecorator, KEY_RUN_CATEGORY, RUN_CATEGORY_DEPLOYMENT
from slipstream.NodeInstance import NodeInstance

from TestCloudConnectorsBase import TestCloudConnectorsBase

import slipstream.wrappers.BaseWrapper
slipstream.wrappers.BaseWrapper.SS_POLLING_INTERVAL_SEC = 1


class TestCloudWrapper(TestCloudConnectorsBase):

    def setUp(self):
        self.serviceurl = 'http://example.com'
        self.config_holder = ConfigHolder(
            {
                'username': base64.b64encode('user'),
                'password': base64.b64encode('pass'),
                'cookie_filename': 'cookies',
                'serviceurl': self.serviceurl,
                'node_instance_name': 'instance-name'
            },
            context={'foo': 'bar'},
            config={'foo': 'bar'})

        os.environ[ENV_CONNECTOR_INSTANCE] = 'Test'

        BaseWrapper.is_mutable = Mock(return_value=False)

    def tearDown(self):
        os.environ.pop(ENV_CONNECTOR_INSTANCE)
        self.config_holder = None
        shutil.rmtree('%s/.cache/' % os.getcwd(), ignore_errors=True)

    def test_get_cloud_name(self):
        for module_name in self.get_cloudconnector_modulenames():
            setattr(self.config_holder, CONFIGPARAM_CONNECTOR_MODULE_NAME, module_name)
            setattr(self.config_holder, KEY_RUN_CATEGORY, RUN_CATEGORY_DEPLOYMENT)
            cw = CloudWrapper(self.config_holder)
            cw.initCloudConnector()

            assert cw._get_cloud_service_name() == 'Test'

    def test_put_image_id(self):
        # pylint: disable=protected-access

        self.config_holder.set(CONFIGPARAM_CONNECTOR_MODULE_NAME,
                               self.get_cloudconnector_modulename_by_cloudname('local'))
        cw = CloudWrapper(self.config_holder)
        cw.initCloudConnector()

        cw._ss_client.httpClient._call = Mock(return_value=Mock())

        cw._update_slipstream_image(NodeInstance({'image.resourceUri': 'module/Name'}), 'ABC')
        cw._ss_client.httpClient._call.assert_called_with(
            '%s/module/Name/Test' % self.serviceurl,
            'PUT', 'ABC', 'application/xml',
            'application/xml', retry=True)

    def test_no_scaling(self):
        """
        No scaling is happening.  Node instances are in terminal states.
        """
        node_instances = {
            'n.1': NodeInstance({NodeDecorator.NODE_INSTANCE_NAME_KEY: 'n.1',
                                 NodeDecorator.SCALE_STATE_KEY: CloudWrapper.SCALE_STATE_OPERATIONAL}),
            'm.1': NodeInstance({NodeDecorator.NODE_INSTANCE_NAME_KEY: 'm.1',
                                 NodeDecorator.SCALE_STATE_KEY: CloudWrapper.SCALE_STATE_GONE})
        }

        cw = CloudWrapper(self.config_holder)
        cw._get_nodes_instances = Mock(return_value=node_instances)

        assert {} == cw._get_effective_scale_states()
        assert None == cw._get_global_scale_state()
        assert False == cw.is_vertical_scaling()

        node_and_instances = cw.get_scaling_node_and_instance_names()
        assert '' == node_and_instances[0]
        assert [] == node_and_instances[1]

    def test_consistent_scale_state_inconsistent_scaling_nodes(self):
        """
        Consistent scale state: only one scaling action at a time on different node instances.
        In case node instance is not in a terminal state (as set on the NodeInstance object),
        we check the state directly on the Run (via CloudWrapper._get_runtime_parameter()).

        Inconsistent scaling nodes: only one node type at a time is allowed to be scaled.
        """
        def _get_runtime_parameter(key):
            if key.endswith(NodeDecorator.NODE_PROPERTY_SEPARATOR + NodeDecorator.SCALE_STATE_KEY):
                return CloudWrapper.SCALE_STATE_RESIZING
            else:
                return 'unknown'

        node_instances = {
            'n.1': NodeInstance({NodeDecorator.NODE_INSTANCE_NAME_KEY: 'n.1',
                                 NodeDecorator.NODE_NAME_KEY: 'n',
                                 NodeDecorator.SCALE_STATE_KEY: 'not terminal'}),
            'n.2': NodeInstance({NodeDecorator.NODE_INSTANCE_NAME_KEY: 'n.2',
                                 NodeDecorator.NODE_NAME_KEY: 'n',
                                 NodeDecorator.SCALE_STATE_KEY: CloudWrapper.SCALE_STATE_OPERATIONAL}),
            'm.1': NodeInstance({NodeDecorator.NODE_INSTANCE_NAME_KEY: 'm.1',
                                 NodeDecorator.NODE_NAME_KEY: 'm',
                                 NodeDecorator.SCALE_STATE_KEY: 'not terminal'}),
            'm.2': NodeInstance({NodeDecorator.NODE_INSTANCE_NAME_KEY: 'm.2',
                                 NodeDecorator.NODE_NAME_KEY: 'm',
                                 NodeDecorator.SCALE_STATE_KEY: CloudWrapper.SCALE_STATE_GONE}),
        }

        cw = CloudWrapper(self.config_holder)
        cw._get_runtime_parameter = Mock(side_effect=_get_runtime_parameter)
        cw._get_nodes_instances = Mock(return_value=node_instances)

        scale_states = cw._get_effective_scale_states()

        assert 1 == len(scale_states)
        assert CloudWrapper.SCALE_STATE_RESIZING in scale_states
        assert 2 == len(scale_states[CloudWrapper.SCALE_STATE_RESIZING])
        assert ['m.1', 'n.1'] == sorted(scale_states[CloudWrapper.SCALE_STATE_RESIZING])

        assert CloudWrapper.SCALE_STATE_RESIZING == cw._get_global_scale_state()

        assert True == cw.is_vertical_scaling()

        self.failUnlessRaises(InconsistentScalingNodesError, cw.get_scaling_node_and_instance_names)

    def test_inconsistent_scale_state_inconsistent_scaling_nodes(self):
        """
        Inconsistent scale state: different scaling actions at a time are not allowed.
        In case node instance is not in a terminal state (as set on the NodeInstance object),
        we check the state directly on the Run (via CloudWrapper._get_runtime_parameter()).

        Inconsistent scaling nodes: only one node type at a time is allowed to be scaled.
        """
        def _get_runtime_parameter(key):
            if key.startswith('n.'):
                return CloudWrapper.SCALE_STATE_RESIZING
            elif key.startswith('m.'):
                return CloudWrapper.SCALE_STATE_DISK_ATTACHING
            else:
                return 'unknown'

        node_instances = {
            'n.1': NodeInstance({NodeDecorator.NODE_INSTANCE_NAME_KEY: 'n.1',
                                 NodeDecorator.NODE_NAME_KEY: 'n',
                                 NodeDecorator.SCALE_STATE_KEY: 'not terminal'}),
            'n.2': NodeInstance({NodeDecorator.NODE_INSTANCE_NAME_KEY: 'n.2',
                                 NodeDecorator.NODE_NAME_KEY: 'n',
                                 NodeDecorator.SCALE_STATE_KEY: CloudWrapper.SCALE_STATE_OPERATIONAL}),
            'm.1': NodeInstance({NodeDecorator.NODE_INSTANCE_NAME_KEY: 'm.1',
                                 NodeDecorator.NODE_NAME_KEY: 'm',
                                 NodeDecorator.SCALE_STATE_KEY: 'not terminal'})
        }

        cw = CloudWrapper(self.config_holder)
        cw._get_runtime_parameter = Mock(side_effect=_get_runtime_parameter)
        cw._get_nodes_instances = Mock(return_value=node_instances)

        scale_states = cw._get_effective_scale_states()

        assert 2 == len(scale_states)

        assert CloudWrapper.SCALE_STATE_RESIZING in scale_states
        assert 1 == len(scale_states[CloudWrapper.SCALE_STATE_RESIZING])
        assert ['n.1'] == scale_states[CloudWrapper.SCALE_STATE_RESIZING]

        assert CloudWrapper.SCALE_STATE_DISK_ATTACHING in scale_states
        assert 1 == len(scale_states[CloudWrapper.SCALE_STATE_DISK_ATTACHING])
        assert ['m.1'] == scale_states[CloudWrapper.SCALE_STATE_DISK_ATTACHING]

        self.failUnlessRaises(InconsistentScaleStateError, cw._get_global_scale_state)
        self.failUnlessRaises(InconsistentScaleStateError, cw.is_vertical_scaling)
        self.failUnlessRaises(InconsistentScaleStateError, cw.check_scale_state_consistency)
        self.failUnlessRaises(InconsistentScalingNodesError, cw.get_scaling_node_and_instance_names)

    def test_consistent_scale_state_consistent_scaling_nodes(self):
        """
        Consistent scale state: different scaling actions at a time are not allowed.
        In case node instance is not in a terminal state (as set on the NodeInstance object),
        we check the state directly on the Run (via CloudWrapper._get_runtime_parameter()).

        Consistent scaling nodes: only one node type at a time is allowed to be scaled.
        """
        def _get_runtime_parameter(key):
            if key.endswith(NodeDecorator.NODE_PROPERTY_SEPARATOR + NodeDecorator.SCALE_STATE_KEY):
                return CloudWrapper.SCALE_STATE_RESIZING
            else:
                return 'unknown'

        node_instances = {
            'n.1': NodeInstance({NodeDecorator.NODE_INSTANCE_NAME_KEY: 'n.1',
                                 NodeDecorator.NODE_NAME_KEY: 'n',
                                 NodeDecorator.SCALE_STATE_KEY: 'not terminal'}),
            'n.2': NodeInstance({NodeDecorator.NODE_INSTANCE_NAME_KEY: 'n.2',
                                 NodeDecorator.NODE_NAME_KEY: 'n',
                                 NodeDecorator.SCALE_STATE_KEY: 'not terminal'}),
            'm.1': NodeInstance({NodeDecorator.NODE_INSTANCE_NAME_KEY: 'm.1',
                                 NodeDecorator.NODE_NAME_KEY: 'm',
                                 NodeDecorator.SCALE_STATE_KEY: CloudWrapper.SCALE_STATE_OPERATIONAL})
        }

        cw = CloudWrapper(self.config_holder)
        cw._get_runtime_parameter = Mock(side_effect=_get_runtime_parameter)
        cw._get_nodes_instances = Mock(return_value=node_instances)

        scale_states = cw._get_effective_scale_states()

        assert 1 == len(scale_states)

        assert CloudWrapper.SCALE_STATE_RESIZING in scale_states
        assert 2 == len(scale_states[CloudWrapper.SCALE_STATE_RESIZING])
        assert ['n.1', 'n.2'] == sorted(scale_states[CloudWrapper.SCALE_STATE_RESIZING])

        assert CloudWrapper.SCALE_STATE_RESIZING == cw._get_global_scale_state()

        try:
            cw.check_scale_state_consistency()
        except InconsistentScaleStateError as ex:
            self.fail('Should not have failed with: %s' % str(ex))

        node_and_instances = cw.get_scaling_node_and_instance_names()
        assert 'n' == node_and_instances[0]
        assert ['n.1', 'n.2'] == sorted(node_and_instances[1])

    def test_vertically_scalle_instances_nowait(self):
        _scale_state = None

        def _get_runtime_parameter(key):
            if key.endswith(NodeDecorator.NODE_PROPERTY_SEPARATOR + NodeDecorator.SCALE_STATE_KEY):
                return _scale_state
            else:
                return 'unknown'

        node_instances = {
            'n.1': NodeInstance({NodeDecorator.NODE_INSTANCE_NAME_KEY: 'n.1',
                                 NodeDecorator.NODE_NAME_KEY: 'n',
                                 NodeDecorator.SCALE_STATE_KEY: CloudWrapper.SCALE_STATE_RESIZING}),
            'n.2': NodeInstance({NodeDecorator.NODE_INSTANCE_NAME_KEY: 'n.2',
                                 NodeDecorator.NODE_NAME_KEY: 'n',
                                 NodeDecorator.SCALE_STATE_KEY: CloudWrapper.SCALE_STATE_DISK_ATTACHING}),
            'n.3': NodeInstance({NodeDecorator.NODE_INSTANCE_NAME_KEY: 'n.3',
                                 NodeDecorator.NODE_NAME_KEY: 'n',
                                 NodeDecorator.SCALE_STATE_KEY: CloudWrapper.SCALE_STATE_DISK_DETACHING}),
            'm.1': NodeInstance({NodeDecorator.NODE_INSTANCE_NAME_KEY: 'm.1',
                                 NodeDecorator.NODE_NAME_KEY: 'm',
                                 NodeDecorator.SCALE_STATE_KEY: CloudWrapper.SCALE_STATE_OPERATIONAL})
        }

        self.config_holder.set('verboseLevel', 3)
        setattr(self.config_holder, 'cloud', 'local')
        setattr(self.config_holder, CONFIGPARAM_CONNECTOR_MODULE_NAME,
                'slipstream.cloudconnectors.dummy.DummyClientCloud')

        cw = CloudWrapper(self.config_holder)
        cw._get_nodes_instances = Mock(return_value=node_instances)
        cw.initCloudConnector(self.config_holder)
        cw._set_runtime_parameter = Mock()

        cw._get_user_timeout = Mock(return_value=2)

        # No waiting.
        cw._wait_pre_scale_done = Mock()
        cw._wait_scale_state = Mock()

        _scale_state = 'resizing'
        cw._get_runtime_parameter = Mock(side_effect=_get_runtime_parameter)
        cw._cloud_client.resize = Mock(wraps=cw._cloud_client.resize)
        cw.vertically_scale_instances()
        assert True == cw._cloud_client.resize.called
        node_instance = cw._cloud_client.resize.call_args[0][0][0]
        assert 'n.1' in node_instance.get_name()
        assert cw._set_runtime_parameter.called_with('n.1:' + NodeDecorator.SCALE_IAAS_DONE, 'true')

        _scale_state = 'disk_attaching'
        cw._get_runtime_parameter = Mock(side_effect=_get_runtime_parameter)
        cw._cloud_client.attach_disk = Mock(wraps=cw._cloud_client.attach_disk)
        cw.vertically_scale_instances()
        assert True == cw._cloud_client.attach_disk.called
        node_instance = cw._cloud_client.attach_disk.call_args[0][0][0]
        assert 'n.2' in node_instance.get_name()
        assert cw._set_runtime_parameter.called_with('n.2:' + NodeDecorator.SCALE_IAAS_DONE, 'true')

        _scale_state = 'disk_detaching'
        cw._get_runtime_parameter = Mock(side_effect=_get_runtime_parameter)
        cw._cloud_client.detach_disk = Mock(wraps=cw._cloud_client.detach_disk)
        cw.vertically_scale_instances()
        assert True == cw._cloud_client.detach_disk.called
        node_instance = cw._cloud_client.detach_disk.call_args[0][0][0]
        assert 'n.3' in node_instance.get_name()
        assert cw._set_runtime_parameter.called_with('n.3:' + NodeDecorator.SCALE_IAAS_DONE, 'true')

    def test_wait_pre_scale_done(self):
        node_instances = [
            NodeInstance({NodeDecorator.NODE_INSTANCE_NAME_KEY: 'n.1'}),
            NodeInstance({NodeDecorator.NODE_INSTANCE_NAME_KEY: 'n.2'}),
            NodeInstance({NodeDecorator.NODE_INSTANCE_NAME_KEY: 'n.3'}),
            NodeInstance({NodeDecorator.NODE_INSTANCE_NAME_KEY: 'm.1'})
        ]
        cw = CloudWrapper(self.config_holder)

        cw.get_pre_scale_done = Mock(return_value='true')
        cw._get_state_timeout_time = Mock(return_value=(time.time() + 10))
        cw._wait_pre_scale_done(node_instances)

        cw.get_pre_scale_done = Mock(return_value='true')
        cw._get_state_timeout_time = Mock(return_value=(time.time() - 1))
        self.failUnlessRaises(TimeoutException, cw._wait_pre_scale_done, node_instances)

        cw.get_pre_scale_done = Mock(return_value='')
        cw._get_state_timeout_time = Mock(return_value=(time.time() + 2))
        self.failUnlessRaises(TimeoutException, cw._wait_pre_scale_done, node_instances)

    def test_wait_scale_state(self):
        node_instances = [
            NodeInstance({NodeDecorator.NODE_INSTANCE_NAME_KEY: 'n.1'}),
            NodeInstance({NodeDecorator.NODE_INSTANCE_NAME_KEY: 'n.2'}),
            NodeInstance({NodeDecorator.NODE_INSTANCE_NAME_KEY: 'n.3'}),
            NodeInstance({NodeDecorator.NODE_INSTANCE_NAME_KEY: 'm.1'})
        ]
        cw = CloudWrapper(self.config_holder)

        # All set before timeout.
        cw._get_effective_scale_state = Mock(return_value=CloudWrapper.SCALE_STATE_RESIZED)
        cw._get_state_timeout_time = Mock(return_value=(time.time() + 5))
        cw._wait_scale_state(CloudWrapper.SCALE_STATE_RESIZED, node_instances)

        # Timeout is in the past.
        cw._get_effective_scale_state = Mock(return_value=CloudWrapper.SCALE_STATE_RESIZED)
        cw._get_state_timeout_time = Mock(return_value=(time.time() - 1))
        self.failUnlessRaises(TimeoutException, cw._wait_scale_state, *(CloudWrapper.SCALE_STATE_RESIZED, node_instances))

        # VMs do not set proper value and we timeout.
        cw._get_effective_scale_state = Mock(return_value=CloudWrapper.SCALE_STATE_RESIZING)
        cw._get_state_timeout_time = Mock(return_value=(time.time() + 2))
        self.failUnlessRaises(TimeoutException, cw._wait_scale_state, *(CloudWrapper.SCALE_STATE_RESIZED, node_instances))


if __name__ == "__main__":
    unittest.main()

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
import unittest

from slipstream.contextualizers.ContextualizerFactory import ContextualizerFactory
from slipstream.ConfigHolder import ConfigHolder
ContextualizerFactory.getContextAsDict = Mock(return_value={'foo':'bar'})
ConfigHolder._getConfigFromFileAsDict = Mock(return_value={'foo':'bar'})

from slipstream.executors.MachineExecutor import MachineExecutor
from slipstream.exceptions.Exceptions import ExecutionException
from slipstream.wrappers.CloudWrapper import CloudWrapper

MachineExecutor.WAIT_NEXT_STATE_SHORT = 1
MachineExecutor.WAIT_NEXT_STATE_LONG = 2


class LocalCacheTestCase(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_wait_for_next_state(self):
        wrapper = Mock(spec=CloudWrapper)
        me = MachineExecutor(wrapper, Mock())

        # Enter the waiting loop just because we are in the Ready state and
        # the run is mutable.  Then exit from the waiting loop immediately with
        # 'NextState' as the next one.
        wrapper.is_mutable = Mock(return_value=True)
        wrapper.getState = Mock(return_value='NextState')
        assert 'NextState' == me._wait_for_next_state('Ready')
        assert 1 == me.wrapper.getState.call_count

        # Enter the waiting loop just because we are in the Ready state and
        # the run is mutable.  Stay in the waiting loop until the state changes.
        me.wrapper.getState.call_count = 0
        wrapper.is_mutable = Mock(return_value=True)
        wrapper.getState = Mock(side_effect=('Ready', 'NextState'))
        assert 'NextState' == me._wait_for_next_state('Ready')
        assert 2 == me.wrapper.getState.call_count

    def test_get_sleep_time(self):
        wrapper = Mock(spec=CloudWrapper)

        me = MachineExecutor(wrapper, Mock())

        # Mutable run on Ready state doesn't wait long.
        # NB! "need to stop images or not" should be ignored.
        wrapper.is_mutable = Mock(return_value=True)
        wrapper.need_to_stop_images = Mock(return_value=False)
        assert me.WAIT_NEXT_STATE_SHORT == me._get_sleep_time('Ready')
        wrapper.need_to_stop_images = Mock(return_value=True)
        assert me.WAIT_NEXT_STATE_SHORT == me._get_sleep_time('Ready')

        # Immutable run on Ready state when no need to stop images waits long.
        wrapper.is_mutable = Mock(return_value=False)
        wrapper.need_to_stop_images = Mock(return_value=False)
        assert me.WAIT_NEXT_STATE_LONG == me._get_sleep_time('Ready')
        # Immutable run on Ready state when need to stop images doesn't wait long.
        wrapper.need_to_stop_images = Mock(return_value=True)
        assert me.WAIT_NEXT_STATE_SHORT == me._get_sleep_time('Ready')

    def test_get_state_retries(self):
        wrapper = Mock(spec=CloudWrapper)

        me = MachineExecutor(wrapper, Mock())

        me.wrapper.getState = Mock(return_value='foo')
        assert 'foo' == me._get_state()

        me.wrapper.getState = Mock(return_value='')
        me._get_state_retry_sleep_times = Mock(return_value=[0.1] * 3)
        self.failUnlessRaises(ExecutionException, me._get_state)

        me.wrapper.getState = Mock(side_effect=['', '', 'bar'])
        me._get_state_retry_sleep_times = Mock(return_value=[0.1] * 3)
        assert 'bar' == me._get_state()


if __name__ == '__main__':
    unittest.main()

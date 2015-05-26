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

from slipstream.ConfigHolder import ConfigHolder
from slipstream.exceptions import Exceptions
from slipstream.executors.MachineExecutor import MachineExecutor
from slipstream.util import override
from slipstream import util


class OrchestratorDeploymentExecutor(MachineExecutor):
    def __init__(self, wrapper, config_holder=ConfigHolder()):
        super(OrchestratorDeploymentExecutor, self).__init__(wrapper,
                                                             config_holder)

    @override
    def onProvisioning(self):
        super(OrchestratorDeploymentExecutor, self).onProvisioning()

        if self._is_vertical_scaling():
            pass
        else:
            self._start_instances()
            self._stop_instances()

        self._complete_state_for_failed_node_instances()

    def _is_vertical_scaling(self):
        # check scale.state is "vertical scaling" i.e. one of <resizing|disk_attaching|disk_detaching>
        return False

    @override
    def onExecuting(self):
        super(OrchestratorDeploymentExecutor, self).onExecuting()
        self._complete_state_for_failed_node_instances()
        self.wrapper.check_scale_state_consistency()

    @override
    def onSendingReports(self):
        super(OrchestratorDeploymentExecutor, self).onSendingReports()
        self._complete_state_for_failed_node_instances()

    @override
    def onReady(self):
        super(OrchestratorDeploymentExecutor, self).onReady()

        self._complete_state_for_failed_node_instances()

        self.wrapper.set_removed_instances_as_gone()

        if not self.wrapper.need_to_stop_images() and not self._is_mutable():
            self._killItself()

    @override
    def onFinalizing(self):
        super(OrchestratorDeploymentExecutor, self).onFinalizing()

        self._run_instances_action(self.wrapper.stopNodes, 'stopping')

        self.wrapper.complete_state()

        self._killItself()

    def _start_instances(self):
        self._run_instances_action(self.wrapper.start_node_instances, 'starting')

    def _stop_instances(self):
        self._run_instances_action(self.wrapper.stop_node_instances, 'stopping')

    @staticmethod
    def _run_instances_action(action, action_name):
        """
        :param action: action to run
        :type action: callable
        :param action_name: name of the action
        :type: string
        """
        util.printStep('%s instances' % action_name.capitalize())
        try:
            action()
        except Exceptions.AbortException:
            pass
        except Exception as ex:
            util.printError('Error %s instances: %s' % (action_name, ex))
            raise

    def _complete_state_for_failed_node_instances(self):
        self.wrapper.complete_state_for_failed_node_instances()

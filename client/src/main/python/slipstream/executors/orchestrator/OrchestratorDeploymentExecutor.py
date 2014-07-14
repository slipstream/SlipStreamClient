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
    def __init__(self, wrapper, configHolder=ConfigHolder()):
        super(OrchestratorDeploymentExecutor, self).__init__(wrapper,
                                                             configHolder)

    @override
    def onProvisioning(self):
        super(OrchestratorDeploymentExecutor, self).onProvisioning()

        self._cleanup_provisioning_info()

        try:
            util.printStep('Starting instances')
            self.wrapper.start_node_instances()
            util.printStep('Removing instances')
            self.wrapper.stop_node_instances()
        except Exceptions.AbortException:
            pass
        except Exception as ex:
            util.printError('Error starting instances with error: %s' % ex)
            raise

    @override
    def onReady(self):
        super(OrchestratorDeploymentExecutor, self).onReady()

        self.wrapper.set_removed_instances_as_gone()

        if not self.wrapper.need_to_stop_images() and not self._is_mutable():
            self._killItself()

    @override
    def onFinalizing(self):
        super(OrchestratorDeploymentExecutor, self).onFinalizing()

        util.printStep('Stopping instances')
        try:
            self.wrapper.stopNodes()
        except Exceptions.AbortException:
            pass
        except Exception as ex:
            util.printError('Error stopping instances: %s' % ex)
            raise

        self.wrapper.complete_state()

        self._killItself()

    def _cleanup_provisioning_info(self):
        self.wrapper.discard_user_info_locally()
        self.wrapper.discard_nodes_info_locally()

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

from slipstream.executors.MachineExecutor import MachineExecutor
from slipstream.NodeDecorator import NodeDecorator
from slipstream.exceptions import Exceptions
from slipstream.util import override
from slipstream import util


class OrchestratorImageBuildExecutor(MachineExecutor):
    def __init__(self, wrapper, configHolder):
        super(OrchestratorImageBuildExecutor, self).__init__(wrapper,
                                                             configHolder)

    @override
    def onProvisioning(self):
        super(OrchestratorImageBuildExecutor, self).onProvisioning()

        util.printStep('Starting instance')
        try:
            self.wrapper.start_node_instances()
        except Exceptions.AbortException:
            pass
        except Exception as ex:
            util.printError('Error starting instance with error: %s' % ex)
            raise
        finally:
            self._complete_machine_state()

    @override
    def onExecuting(self):
        super(OrchestratorImageBuildExecutor, self).onExecuting()
        if self.wrapper.isAbort():
            util.printError('Abort set, skipping Running')
            self._complete_machine_state()
            return

        util.printStep('Building new image')

        try:
            self.wrapper.build_image()
        except KeyboardInterrupt:
            raise
        except Exception as ex:
            self.wrapper.fail(str(ex))
        finally:
            self._complete_machine_state()

    @override
    def onSendingReports(self):
        super(OrchestratorImageBuildExecutor, self).onSendingReports()
        self._complete_machine_state()

    @override
    def onReady(self):
        super(OrchestratorImageBuildExecutor, self).onReady()
        self._complete_machine_state()

    @override
    def onFinalizing(self):
        super(OrchestratorImageBuildExecutor, self).onFinalizing()
        self._killCreator()
        self._complete_machine_state()

        self.wrapper.complete_state()

        self._killItself(True)

    def _killCreator(self):
        self.wrapper.stopCreator()

    def _complete_machine_state(self):
        self.wrapper.clientSlipStream.complete_state(NodeDecorator.MACHINE_NAME)

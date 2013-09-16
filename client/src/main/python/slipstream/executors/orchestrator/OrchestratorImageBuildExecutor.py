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
from slipstream import util


class OrchestratorImageBuildExecutor(MachineExecutor):
    def __init__(self, wrapper, configHolder):
        super(OrchestratorImageBuildExecutor, self).__init__(wrapper, configHolder)

    def onInitializing(self):
        super(OrchestratorImageBuildExecutor, self).onInitializing()

        util.printStep('Starting instance')
        try:
            self.wrapper.startImage()
        except Exceptions.AbortException:
            pass
        except Exception, ex:
            util.printError('Error starting instance with error: %s' % ex)
            raise
        finally:
            self._advanceMachine()

        util.printStep('Publishing instance initialization information')
        self.wrapper.publishDeploymentInitializationInfo()

    def onRunning(self):
        super(OrchestratorImageBuildExecutor, self).onRunning()
        if self.wrapper.isAbort():
            util.printError('Abort set, skipping Running')
            self._advanceMachine()
            return

        util.printStep('Building new image')

        try:
            self.wrapper.buildImage()
            self.wrapper.updateSlipStreamImage()
        except KeyboardInterrupt:
            raise
        except Exception, ex:
            self.wrapper.fail(str(ex))
        finally:
            self._advanceMachine()

    def onSendingFinalReport(self):
        super(OrchestratorImageBuildExecutor, self).onSendingFinalReport()
        self._advanceMachine()

    def onFinalizing(self):
        super(OrchestratorImageBuildExecutor, self).onFinalizing()
        self._advanceMachine()
        self._killCreator()
        self._killItself()

    def _killCreator(self):
        creatorVmId = self.wrapper.getCreatorVmId()
        if creatorVmId:
            util.printDetail('Stop creator: %s' % creatorVmId)
            self.wrapper.stopImages([creatorVmId])

    def _advanceMachine(self):
        self.wrapper.clientSlipStream.advance(NodeDecorator.MACHINE_NAME)

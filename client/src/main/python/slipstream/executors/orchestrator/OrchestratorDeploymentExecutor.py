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
from slipstream import util


class OrchestratorDeploymentExecutor(MachineExecutor):
    def __init__(self, wrapper, configHolder=ConfigHolder()):
        super(OrchestratorDeploymentExecutor, self).__init__(wrapper,
                                                             configHolder)

    def onProvisioning(self):
        util.printAction('Provisioning')
        util.printStep('Starting instances')
        try:
            self.wrapper.startImages()
        except Exceptions.AbortException:
            pass
        except Exception as ex:
            util.printError('Error starting instances with error: %s' % ex)
            raise

        util.printStep('Publishing instance initialization information')
        self.wrapper.publishDeploymentInitializationInfo()

    def onReady(self):
        super(OrchestratorDeploymentExecutor, self).onReady()

        if not self.wrapper.needToStopImages():
            self._killItself()

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

        self.wrapper.advance()

        self._killItself()

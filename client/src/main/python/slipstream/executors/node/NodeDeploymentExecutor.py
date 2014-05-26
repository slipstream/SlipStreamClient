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

import os
import time
import codecs
import tempfile

from slipstream.ConfigHolder import ConfigHolder
from slipstream.executors.MachineExecutor import MachineExecutor
import slipstream.util as util
from slipstream.exceptions.Exceptions import ExecutionException
from slipstream.util import appendSshPubkeyToAuthorizedKeys


def getExecutor(wrapper, configHolder):
    return NodeDeploymentExecutor(wrapper, configHolder)


class NodeDeploymentExecutor(MachineExecutor):
    def __init__(self, wrapper, configHolder=ConfigHolder()):
        self.verboseLevel = 0
        super(NodeDeploymentExecutor, self).__init__(wrapper, configHolder)
        self.targets = {}

    def onProvisioning(self):
        util.printAction('Provisioning')

        self._addSshPubkeyIfNeeded()

        util.printStep('Getting deployment targets')

        self.targets = self.wrapper.getTargets()

        util.printDetail('Deployment targets:')
        for target, script in self.targets.items():
            util.printAndFlush('-' * 25)
            util.printDetail('Target: %s' % target)
            util.printDetail('Script:\n%s\n' % script[0])

    def onExecuting(self):
        util.printAction('Executing')
        self._executeTarget('execute')

    def onSendingReports(self):
        util.printAction('Sending report')
        try:
            self._executeTarget('report')
        except ExecutionException as ex:
            util.printDetail("Failed executing 'report' with: \n%s" % str(ex),
                             verboseLevel=self.verboseLevel,
                             verboseThreshold=util.VERBOSE_LEVEL_NORMAL)
            raise
        finally:
            super(NodeDeploymentExecutor, self).onSendingReports()
            
    def onFinalizing(self):
        super(NodeDeploymentExecutor, self).onSendingReports()
        
    def onDone(self):
        time.sleep(60)
        raise ExecutionException('The run is in Done state but the VM is still running !')

    def _executeTarget(self, target):
        util.printStep("Executing target '%s'" % target)
        if target in self.targets:
            tmpfilesuffix = ''
            if util.isWindows():
                tmpfilesuffix = '.ps1'
            fn = tempfile.mktemp(suffix=tmpfilesuffix)
            if isinstance(self.targets[target][0], unicode):
                with codecs.open(fn, 'w', 'utf8') as fh:
                    fh.write(self.targets[target][0])
            else:
                with open(fn, 'w') as fh:
                    fh.write(self.targets[target][0])
            os.chmod(fn, 0755)
            currentDir = os.getcwd()
            os.chdir(tempfile.gettempdir() + os.sep)
            try:
                self._executeRaiseOnError(fn)
            finally:
                os.chdir(currentDir)
        else:
            print 'Nothing to do'

    def _addSshPubkeyIfNeeded(self):
        if util.needToAddSshPubkey():
            self._addSshPubkey()

    def _addSshPubkey(self):
        util.printStep('Adding the public key')
        appendSshPubkeyToAuthorizedKeys(self._getUserSshPubkey())

    def _getUserSshPubkey(self):
        return self.wrapper.getUserSshPubkey()

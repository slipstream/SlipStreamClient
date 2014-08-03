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
import sys
import time
import codecs
import tempfile

from slipstream.ConfigHolder import ConfigHolder
from slipstream.executors.MachineExecutor import MachineExecutor
import slipstream.util as util
from slipstream.exceptions.Exceptions import ExecutionException
from slipstream.util import appendSshPubkeyToAuthorizedKeys, override

TARGET_POLL_INTERVAL = 10  # Time to wait (in seconds) between to server call
                           # while executing a target script.


def getExecutor(wrapper, configHolder):
    return NodeDeploymentExecutor(wrapper, configHolder)


class NodeDeploymentExecutor(MachineExecutor):

    def __init__(self, wrapper, configHolder=ConfigHolder()):
        self.verboseLevel = 0
        super(NodeDeploymentExecutor, self).__init__(wrapper, configHolder)
        self.targets = {}

    @override
    def onProvisioning(self):
        super(NodeDeploymentExecutor, self).onProvisioning()

        if self.wrapper.is_scale_state_creating():
            self._add_ssh_pubkey_if_needed()
            self.wrapper.set_scale_state_created()

        util.printStep('Getting execution targets')
        self.targets = self.wrapper.getTargets()

        util.printDetail('Available execution targets:')
        for target, script in self.targets.items():
            util.printDetail('Target: %s' % target, timestamp=False)
            util.printDetail('Script:\n%s\n' % script[0], timestamp=False)

    @override
    def onExecuting(self):
        util.printAction('Executing')
        self._executeTarget('execute')

    @override
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

    @override
    def onFinalizing(self):
        super(NodeDeploymentExecutor, self).onSendingReports()

    @override
    def onReady(self):
        super(NodeDeploymentExecutor, self).onReady()
        self.wrapper.set_scale_state_operational()

    def _executeTarget(self, target):
        util.printStep("Executing target '%s'" % target)
        if target in self.targets:
            self._run_target_script(self.targets[target][0])
            sys.stdout.flush()
            sys.stderr.flush()
        else:
            util.printAndFlush('Nothing to do\n')

    def _run_target_script(self, target_script):
        if not target_script:
            util.printAndFlush('Script is empty\n')
            return

        tmpfilesuffix = ''
        if util.is_windows():
            tmpfilesuffix = '.ps1'
        fn = tempfile.mktemp(suffix=tmpfilesuffix)
        if isinstance(target_script, unicode):
            with codecs.open(fn, 'w', 'utf8') as fh:
                fh.write(target_script)
        else:
            with open(fn, 'w') as fh:
                fh.write(target_script)
        os.chmod(fn, 0755)
        currentDir = os.getcwd()
        os.chdir(tempfile.gettempdir() + os.sep)
        try:
            process = util.execute(fn, noWait=True)
        finally:
            os.chdir(currentDir)

        # The process is still working on the background.
        while process.poll() is None:
            # Ask server whether the abort flag is set. If so, kill the
            # process and exit. Otherwise, sleep for some time.
            if self.wrapper.isAbort():
                try:
                    util.printDetail('Abort flag detected. '
                                     'Terminating target script execution...')
                    process.terminate()
                    time.sleep(5)
                    if process.poll() is None:
                        util.printDetail('Termination is taking too long. '
                                         'Killing the target script...')
                        process.kill()
                except OSError:
                    pass
                break
            time.sleep(TARGET_POLL_INTERVAL)
        util.printDetail("End of the target script")

    def _add_ssh_pubkey_if_needed(self):
        # if util.needToAddSshPubkey():
        self._add_ssh_pubkey()

    def _add_ssh_pubkey(self):
        util.printStep('Adding the public keys')
        appendSshPubkeyToAuthorizedKeys(self._get_user_ssh_pubkey())

    def _get_user_ssh_pubkey(self):
        return self.wrapper.get_user_ssh_pubkey()



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

import os
import sys
import time
import codecs
import tempfile

from slipstream.ConfigHolder import ConfigHolder
from slipstream.executors.MachineExecutor import MachineExecutor
import slipstream.util as util
from slipstream.exceptions.Exceptions import ExecutionException, \
    AbortException
from slipstream.util import appendSshPubkeyToAuthorizedKeys, override


def getExecutor(wrapper, configHolder):
    return NodeDeploymentExecutor(wrapper, configHolder)


class NodeDeploymentExecutor(MachineExecutor):

    SCRIPT_EXIT_SUCCESS = 0

    # Wait interval (seconds) between server calls when executing a target script.
    TARGET_POLL_INTERVAL = 10

    def __init__(self, wrapper, configHolder=ConfigHolder()):
        self.verboseLevel = 0
        super(NodeDeploymentExecutor, self).__init__(wrapper, configHolder)
        self.targets = {}

        self.SCALE_ACTION_TO_TARGET = \
            {self.wrapper.SCALE_ACTION_CREATION: 'onvmadd',
             self.wrapper.SCALE_ACTION_REMOVAL: 'onvmremove',
             self.wrapper.SCALE_ACTION_DISK_RESIZE: 'ondiskresize'}

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

        if not self.wrapper.is_scale_state_operational():
            self._execute_target('execute', abort_on_err=True)
        else:
            self._execute_scale_action_target()

    @override
    def onSendingReports(self):
        util.printAction('Sending report')
        try:
            self._execute_target('report')
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

    def _get_target_on_scale_action(self, action):
        return self.SCALE_ACTION_TO_TARGET.get(action, None)

    def _execute_scale_action_target(self):
        scale_action = self.wrapper.get_global_scale_action()
        if scale_action:
            # TODO: Add local scale actions (ondiskresize, etc)
            target = self._get_target_on_scale_action(scale_action)
            if target:
                exports = self._get_scaling_exports()
                self._execute_target(target, exports)
            else:
                util.printDetail("Deployment is scaling. No target to "
                                 "execute on action %s" % scale_action)
        else:
            util.printDetail("WARNING: deployment is scaling, but no "
                             "scaling action defined.")

    def _execute_target(self, target, exports={}, abort_on_err=False):
        util.printStep("Executing target '%s'" % target)
        if target in self.targets:
            self._launch_target_script(target, exports, abort_on_err)
        else:
            util.printAndFlush('Nothing to do on target: %s\n' % target)

    def _launch_target_script(self, target, exports, abort_on_err):
        fail_msg = "Failed running '%s' target on '%s'" % (
            target, self._get_node_instance_name())
        try:
            rc = self._run_target_script(self.targets[target][0], exports)
            sys.stdout.flush()
            sys.stderr.flush()
        except Exception as ex:
            msg = '%s: %s' % (fail_msg, str(ex))
            if abort_on_err:
                self.wrapper.fail(msg)
            raise
        else:
            if rc != self.SCRIPT_EXIT_SUCCESS and abort_on_err:
                self.wrapper.fail(fail_msg)
                raise AbortException(fail_msg)

    def _get_scaling_exports(self):
        node_name, node_instance_names = \
            self.wrapper.get_scaling_node_and_instance_names()
        exports = {'SLIPSTREAM_SCALING_NODE': node_name,
                   'SLIPSTREAM_SCALING_VMS': ' '.join(node_instance_names)}
        return exports

    def _launch_process(self, target_script, exports):
        '''Returns launched process as subprocess.Popen instance.
        '''
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
            process = util.execute(fn, noWait=True, extra_env=exports)
        finally:
            os.chdir(currentDir)

        return process

    def _run_target_script(self, target_script, exports={}):
        '''Return exit code of the user script.  Output of the script goes
        to stdout/err and will end up in the node executor's log file.
        '''
        if not target_script:
            util.printAndFlush('Script is empty\n')
            return self.SCRIPT_EXIT_SUCCESS

        process = self._launch_process(target_script, exports)

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
            time.sleep(self.TARGET_POLL_INTERVAL)
        util.printDetail("End of the target script")

        return process.returncode

    def _add_ssh_pubkey_if_needed(self):
        # if util.needToAddSshPubkey():
        self._add_ssh_pubkey()

    def _add_ssh_pubkey(self):
        util.printStep('Adding the public keys')
        appendSshPubkeyToAuthorizedKeys(self._get_user_ssh_pubkey())

    def _get_user_ssh_pubkey(self):
        return self.wrapper.get_user_ssh_pubkey()

    def _get_node_instance_name(self):
        return self.wrapper.node_instance_name()

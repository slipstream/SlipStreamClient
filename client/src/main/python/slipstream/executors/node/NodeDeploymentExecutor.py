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

from slipstream.ConfigHolder import ConfigHolder
from slipstream.executors.MachineExecutor import MachineExecutor
from slipstream import util
from slipstream.exceptions.Exceptions import ExecutionException, AbortException, \
    InconsistentScaleStateError
from slipstream.util import append_ssh_pubkey_to_authorized_keys, override
from slipstream.NodeDecorator import NodeDecorator


def getExecutor(wrapper, configHolder):
    return NodeDeploymentExecutor(wrapper, configHolder)


class NodeDeploymentExecutor(MachineExecutor):

    def __init__(self, wrapper, config_holder=ConfigHolder()):
        self.verboseLevel = 0
        super(NodeDeploymentExecutor, self).__init__(wrapper, config_holder)

        self.SCALE_ACTION_TO_TARGET = \
            {self.wrapper.SCALE_ACTION_CREATION: 'onvmadd',
             self.wrapper.SCALE_ACTION_REMOVAL: 'onvmremove'}

        self._skip_execute_due_to_vertical_scaling = False

    @override
    def onProvisioning(self):
        super(NodeDeploymentExecutor, self).onProvisioning()

        if self.wrapper.is_scale_state_creating():
            self._add_ssh_pubkey(self.node_instance.get_username())
            self.wrapper.set_scale_state_created()
        elif self._is_vertical_scaling():
            if not self._is_pre_scale_done():
                self._execute_pre_scale_action_target()
                self.wrapper.set_pre_scale_done()

            # Orchestrator applies IaaS action on the node instance.

            self.wrapper.wait_scale_iaas_done()
            self.wrapper.unset_pre_scale_done()
            self._execute_post_scale_action_target()
            self.wrapper.set_scale_action_done()
            self._skip_execute_due_to_vertical_scaling = True
        elif self._is_horizontal_scale_down():
            self._execute_pre_scale_action_target()
            self._execute_report_target_and_send_reports()
            self.wrapper.set_pre_scale_done()
            # We are ready to be terminated.

    @override
    def onExecuting(self):
        util.printAction('Executing')

        self._get_recovery_mode()
        if self._is_recovery_mode():
            util.printDetail("Recovery mode enabled, recipes will not be executed.",
                             verboseThreshold=util.VERBOSE_LEVEL_QUIET)
            return

        if self._skip_execute_due_to_vertical_scaling:
            util.printDetail("Vertical scaling: skipping execution of execute targets.",
                             verboseThreshold=util.VERBOSE_LEVEL_QUIET)
            self._skip_execute_due_to_vertical_scaling = False
            return

        if not self.wrapper.is_scale_state_operational():
            self._execute_build_recipes()
            self._execute_execute_target()
        else:
            self._execute_scale_action_target()

    def _execute_build_recipes(self):
        util.printDetail('Executing build recipes')

        self._execute_target(NodeDecorator.NODE_PRERECIPE, abort_on_err=True)
        self._install_user_packages()
        self._execute_target(NodeDecorator.NODE_RECIPE, abort_on_err=True)

    def _install_user_packages(self):
        util.printAndFlush('Installing packages')

        if self.is_image_builded():
            util.printAndFlush('Component already built. No packages to install')
            return

        packages = self.node_instance.get_packages()
        if packages:
            message = 'Installing packages: %s' % ', '.join(packages)
            fail_msg = "Failed installing packages on '%s'" % self._get_node_instance_name()
            util.printStep(message)
            self.wrapper.set_statecustom(message)
            cmd = util.get_packages_install_command(self.node_instance.get_platform(), packages)
            self._launch_script('#!/bin/sh -xe\n%s' % cmd, fail_msg=fail_msg)
        else:
            util.printAndFlush('No packages to install')

    @override
    def onSendingReports(self):
        util.printAction('Sending report')

        if self._need_to_send_reports():
            self._execute_report_target_and_send_reports()
            self._unset_need_to_send_reports()
        else:
            util.printDetail('INFO: Conditionally skipped sending reports.',
                             verboseThreshold=util.VERBOSE_LEVEL_QUIET)
        self.wrapper.set_scale_state_operational()

    def _execute_report_target_and_send_reports(self):
        exports = {'SLIPSTREAM_REPORT_DIR': util.get_platform_reports_dir()}
        try:
            self._execute_target('report', exports=exports, ssdisplay=False, ignore_abort=True)
        except ExecutionException as ex:
            util.printDetail("Failed executing 'report' with: \n%s" % str(ex),
                             verboseLevel=self.verboseLevel,
                             verboseThreshold=util.VERBOSE_LEVEL_NORMAL)
            raise
        finally:
            super(NodeDeploymentExecutor, self).onSendingReports()

    @override
    def onReady(self):
        super(NodeDeploymentExecutor, self).onReady()

    def _get_target_on_scale_action(self, action):
        return self.SCALE_ACTION_TO_TARGET.get(action, None)

    def _execute_pre_scale_action_target(self):
        exports = self._get_scaling_exports()
        self._execute_target('prescale', exports)
        self._set_need_to_send_reports()

    def _execute_post_scale_action_target(self):
        exports = self._get_scaling_exports()
        self._execute_target('postscale', exports)
        self._set_need_to_send_reports()

    def _execute_scale_action_target(self):
        scale_action = self._get_global_scale_action()
        if scale_action:
            target = self._get_target_on_scale_action(scale_action)
            if target:
                exports = self._get_scaling_exports()
                self._execute_target(target, exports)
                self._set_need_to_send_reports()
            else:
                util.printDetail("Deployment is scaling. No target to "
                                 "execute on action %s" % scale_action)
        else:
            util.printDetail("WARNING: deployment is scaling, but no "
                             "scaling action defined.")

    def _get_scaling_exports(self):
        node_name, node_instance_names = \
            self.wrapper.get_scaling_node_and_instance_names()
        exports = {'SLIPSTREAM_SCALING_NODE': node_name,
                   'SLIPSTREAM_SCALING_VMS': ' '.join(node_instance_names),
                   'SLIPSTREAM_SCALING_ACTION': self._get_scale_action()}
        return exports

    def _add_ssh_pubkey(self, login_user):
        if not util.is_windows():
            util.printStep('Adding the public keys')
            append_ssh_pubkey_to_authorized_keys(self._get_user_ssh_pubkey(), login_user)

    def _get_user_ssh_pubkey(self):
        return self.wrapper.get_user_ssh_pubkey()

    def _unset_need_to_send_reports(self):
        self._send_reports = False

    def _need_to_send_reports(self):
        return self._send_reports or not self.wrapper.is_scale_state_operational()

    def _get_scale_action(self):
        return self.wrapper.get_scale_action()

    def _get_global_scale_action(self):
        return self.wrapper.get_global_scale_action()

    def _is_pre_scale_done(self):
        return self.wrapper.is_pre_scale_done()

    def _is_vertical_scaling(self):
        return self.wrapper.is_vertical_scaling_vm()

    def _is_horizontal_scale_down(self):
        try:
            return self.wrapper.is_horizontal_scale_down_vm()
        except InconsistentScaleStateError as ex:
            util.printDetail("Machine Executor. Ignoring exception: %s" % str(ex))
            return False


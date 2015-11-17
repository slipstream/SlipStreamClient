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
import time
import traceback
import tarfile
import tempfile
import random

from slipstream.ConfigHolder import ConfigHolder
from slipstream.exceptions.Exceptions import AbortException, \
    TerminalStateException, ExecutionException
from slipstream import util


class MachineExecutor(object):

    WAIT_NEXT_STATE_SHORT = 15
    WAIT_NEXT_STATE_LONG = 60
    EMPTY_STATE_RETRIES_NUM = 4

    def __init__(self, wrapper, config_holder=ConfigHolder()):
        """
        :param wrapper: SlipStream client and cloud client wrapper
        :type wrapper: slipstream.wrappers.CloudWrapper
        :param config_holder: configuration holder
        :type config_holder: slipstream.ConfigHolder
        """
        self.wrapper = wrapper
        self.timeout = 55 * 60  # 50 minutes
        self.ssLogDir = util.REPORTSDIR
        self.verboseLevel = 0
        config_holder.assign(self)

        self.reportFilesAndDirsList = [self.ssLogDir]

    def execute(self):
        try:
            self._execute()
        except Exception as ex:
            self._fail_global(ex)

    def _execute(self):
        state = self._get_state()
        while True:
            self._execute_state(state)
            self._complete_state(state)
            state = self._wait_for_next_state(state)

    def _get_state(self):
        state = self.wrapper.getState()
        if state:
            return state
        else:
            for stime in self._get_state_retry_sleep_times():
                util.printDetail('WARNING: Got no state. Retrying after %s sec.' % stime)
                self._sleep(stime)
                state = self.wrapper.getState()
                if state:
                    return state
        raise ExecutionException('ERROR: Machine executor: Got no state from server.')

    def _get_state_retry_sleep_times(self):
        return [1] + random.sample(range(1, self.EMPTY_STATE_RETRIES_NUM + 2),
                                   self.EMPTY_STATE_RETRIES_NUM)

    def _execute_state(self, state):
        if not state:
            raise ExecutionException('ERROR: Machine executor: No state to execute '
                                     'specified.')
        try:
            self._set_state_start_time()
            method_name = 'on' + state
            if hasattr(self, method_name):
                getattr(self, method_name)()
            else:
                self._state_not_implemented(state)
        except AbortException as ex:
            util.printError('Abort flag raised: %s' % ex)
        except TerminalStateException:
            return
        except KeyboardInterrupt:
            raise
        except (SystemExit, Exception) as ex:
            if isinstance(ex, SystemExit) and str(ex).startswith('Terminating on signal'):
                self._log_and_set_statecustom('Machine executor is stopping with: %s' % ex)
            else:
                util.printError('Error executing node, with detail: %s' % ex)
                traceback.print_exc()
                self._fail(ex)
            self.onSendingReports()

    def _state_not_implemented(self, state):
        msg = "Machine executor does not implement '%s' state." % state
        traceback.print_exc()
        self._fail_str(msg)
        self.onSendingReports()

    def _complete_state(self, state):
        if self._need_to_complete(state):
            self.wrapper.complete_state()

    @staticmethod
    def _failure_msg_from_exception(exception):
        """
        :param exception: exception class
        :return: string
        """
        return "Exception %s with detail: %s" % (exception.__class__, str(exception))

    def _fail(self, exception):
        self.wrapper.fail(self._failure_msg_from_exception(exception))

    def _fail_global(self, exception):
        self.wrapper.fail_global(self._failure_msg_from_exception(exception))

    def _fail_str(self, msg):
        self.wrapper.fail(msg)

    def _wait_for_next_state(self, state):
        """Returns the next state after waiting (polling is used) for the state
        transition from the server.
        """
        util.printDetail('Waiting for the next state transition, currently in %s' % state,
                         self.verboseLevel, util.VERBOSE_LEVEL_NORMAL)

        while True:
            new_state = self.wrapper.getState()
            if state != new_state:
                return new_state
            self._sleep(self._get_sleep_time(state))

    def _in_ready_and_no_need_to_stop_images(self, state):
        return state == 'Ready' and not self.wrapper.need_to_stop_images()

    def _in_ready_and_mutable_run(self, state):
        return state == 'Ready' and self._is_mutable()

    @staticmethod
    def _sleep(seconds):
        util.sleep(seconds)

    def _get_sleep_time(self, state):
        if not self._is_mutable() and self._in_ready_and_no_need_to_stop_images(state):
            return self.WAIT_NEXT_STATE_LONG
        return self.WAIT_NEXT_STATE_SHORT

    def _is_mutable(self):
        return self.wrapper.is_mutable()

    def _need_to_complete(self, state):
        return state not in ['Finalizing', 'Done', 'Cancelled', 'Aborted']

    def onInitializing(self):
        util.printAction('Initializing')

    def onProvisioning(self):
        util.printAction('Provisioning')

        self._clean_user_info_cache()
        self._clean_local_cache()

    def _clean_user_info_cache(self):
        self.wrapper.discard_user_info_locally()

    def _clean_local_cache(self):
        self.wrapper.clean_local_cache()

    def onExecuting(self):
        util.printAction('Executing')

    def onSendingReports(self):
        util.printAction('Sending reports')
        reportFileName = '%s_report_%s.tgz' % (
            self._get_node_instance_name(), util.toTimeInIso8601NoColon(time.time()))
        reportFileName = os.path.join(tempfile.gettempdir(), reportFileName)
        try:
            archive = tarfile.open(reportFileName, 'w:gz')
            for element in self.reportFilesAndDirsList:
                archive.add(element)
        except Exception as e:
            raise RuntimeError("Failed to bundle reports:\n%s" % e)
        archive.close()

        self.wrapper.send_report(reportFileName)

    def onReady(self):
        util.printAction('Ready')

    def onFinalizing(self):
        util.printAction('Finalizing')

        if self.wrapper.isAbort():
            util.printError("Failed")
        else:
            util.printAction('Done!')

    def onDone(self):
        self._abort_running_in_final_state()

    def onCancelled(self):
        self._abort_running_in_final_state()

    def onAborted(self):
        self._abort_running_in_final_state()

    def _abort_running_in_final_state(self):
        time.sleep(60)
        raise ExecutionException('The run is in a final state but the VM is still running !')

    def _get_node_instance_name(self):
        return self.wrapper.get_my_node_instance_name()

    def _killItself(self, is_build_image=False):
        self.wrapper.stopOrchestrator(is_build_image)

    def _set_state_start_time(self):
        self.wrapper.set_state_start_time()

    def _log_and_set_statecustom(self, msg):
        self.wrapper._log_and_set_statecustom(msg)


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
import re
import sys
import time
import errno
import codecs
import traceback
import tarfile
import tempfile
import random

from Queue import Queue, Empty
from threading import Thread

from slipstream.ConfigHolder import ConfigHolder
from slipstream.exceptions.Exceptions import AbortException, TerminalStateException, ExecutionException
from slipstream.NodeDecorator import NodeDecorator
from slipstream import util


class MachineExecutor(object):

    WAIT_NEXT_STATE_SHORT = 15
    WAIT_NEXT_STATE_LONG = 60
    EMPTY_STATE_RETRIES_NUM = 4

    # Wait interval (seconds) between server calls when executing a target script.
    TARGET_POLL_INTERVAL = 10
    SCRIPT_EXIT_SUCCESS = 0

    def __init__(self, wrapper, config_holder=ConfigHolder()):
        """
        :param wrapper: SlipStream client and cloud client wrapper
        :type wrapper: slipstream.wrappers.CloudWrapper
        :param config_holder: configuration holder
        :type config_holder: slipstream.ConfigHolder
        """
        self.wrapper = wrapper
        self.timeout = 55 * 60  # 55 minutes
        self.ssLogDir = util.get_platform_reports_dir()
        self.verboseLevel = 0
        config_holder.assign(self)

        self.reportFilesAndDirsList = [self.ssLogDir]

        self.node_instance = self._retrieve_my_node_instance()
        self.recovery_mode = False
        self._send_reports = False

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
            new_state = self._get_state()
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

    def _retrieve_my_node_instance(self):
        node_instance = self.wrapper.get_my_node_instance()
        if node_instance is None:
            raise ExecutionException("Couldn't get the node instance for the current VM.")
        return node_instance

    def _get_recovery_mode(self):
        self.recovery_mode = self.wrapper.get_recovery_mode()

    def _is_recovery_mode(self):
        return self.recovery_mode == True

    def _is_mutable(self):
        return self.wrapper.is_mutable()

    def _need_to_complete(self, state):
        return state not in ['Finalizing', 'Done', 'Cancelled', 'Aborted']

    def _set_need_to_send_reports(self):
        self._send_reports = True

    def _execute_execute_target(self):
        self._execute_target('execute', abort_on_err=True)
        self._set_need_to_send_reports()

    def _execute_target(self, target_name, exports=None, abort_on_err=False, ssdisplay=True, ignore_abort=False):
        target = self.node_instance.get_image_target(target_name)

        display_target_name = {
            'prerecipe': 'Pre-install',
            'recipe': 'Post-install',
            'execute': 'Deployment',
            'report': 'Reporting',
            'onvmadd': 'On VM Add',
            'onvmremove': 'On VM Remove'
        }.get(target_name, target_name)

        if target is None:
            util.printAndFlush('Nothing to do for script: %s' % display_target_name)
            return

        for subtarget in target:
            full_target_name = '%s:%s' % (subtarget.get('module_uri'), display_target_name)

            if target_name in [NodeDecorator.NODE_PRERECIPE, NodeDecorator.NODE_RECIPE] \
                    and not self._need_to_execute_build_step(target, subtarget):
                util.printAndFlush('Component already built. Nothing to do on target: %s' % full_target_name)
                continue

            script = subtarget.get('script')
            if script:
                message = "Executing script '%s'" % full_target_name
                util.printStep(message)
                if ssdisplay:
                    self.wrapper.set_statecustom(message)

                fail_msg = "Failed running '%s' script on '%s'" % (full_target_name, self._get_node_instance_name())
                self._launch_script(script, exports, abort_on_err, ignore_abort, fail_msg, full_target_name)
            else:
                util.printAndFlush('Nothing to do for script: %s' % full_target_name)

    def _need_to_execute_build_step(self, target, subtarget):
        return MachineExecutor.need_to_execute_build_step(self._get_node_instance(), target, subtarget)

    @staticmethod
    def need_to_execute_build_step(node_instance, target, subtarget):
        module_uri = subtarget.get('module_uri')
        build_states = node_instance.get_build_state()
        cloud = node_instance.get_cloud()

        for st in reversed(target):
            st_module_uri = st.get('module_uri')
            build_state = build_states.get(st_module_uri, {})

            if cloud in build_state.get('built_on', []):
                return False
            if st_module_uri == module_uri:
                return True

        return True

    def is_image_built(self):
        node_instance = self._get_node_instance()
        module_uri = node_instance.get_image_resource_uri()
        build_state = node_instance.get_build_state().get(module_uri, {})
        cloud = node_instance.get_cloud()

        return cloud in build_state.get('built_on', [])

    def _get_script_name(self, name):
        return name if name is not None else NodeDecorator.DEFAULT_SCRIPT_NAME

    def _launch_script(self, script, exports=None, abort_on_err=True, ignore_abort=False, fail_msg=None, name=None):
        _name = self._get_script_name(name)

        if fail_msg is None:
            fail_msg = "Failed running script '%s' on '%s'" % (_name, self._get_node_instance_name())

        try:
            rc, stderr_last_line = self._run_target_script(script, exports, ignore_abort=ignore_abort, name=name)
            sys.stdout.flush()
            sys.stderr.flush()
        except Exception as ex:
            msg = '%s: %s' % (fail_msg, str(ex))
            if abort_on_err:
                self.wrapper.fail(msg)
            raise
        else:
            if rc != self.SCRIPT_EXIT_SUCCESS and abort_on_err:
                if stderr_last_line is not None:
                    fail_msg += ': %s' % stderr_last_line
                self.wrapper.fail(fail_msg)
                raise AbortException(fail_msg)

    def _run_target_script(self, target_script, exports=None, ignore_abort=False, name=None):
        '''Return exit code of the user script and the last line of stderr
        Output of the script goes to stdout/err and will end up in the node executor's log file.
        '''
        _name = self._get_script_name(name)

        if not target_script:
            util.printAndFlush('Script "%s" is empty\n' % (_name,))
            return self.SCRIPT_EXIT_SUCCESS

        if not isinstance(target_script, basestring):
            raise ExecutionException('Not a string buffer provided as target for script "%s". Type is: %s'
                                     % (_name, type(target_script)))

        process = self._launch_process(target_script, exports, name)

        result = Queue()
        t = Thread(target=self.print_and_keep_last_stderr, args=(process.stderr, result))
        t.daemon = True # thread dies with the program
        t.start()

        try:
            # The process is still working on the background.
            while process.poll() is None:
                # Ask server whether the abort flag is set. If so, kill the
                # process and exit. Otherwise, sleep for some time.
                if not ignore_abort and self.wrapper.isAbort():
                    try:
                        util.printDetail('Abort flag detected. '
                                         'Terminating execution of script "%s"...' % (_name,))
                        process.terminate()
                        util.sleep(5)
                        if process.poll() is None:
                            util.printDetail('Termination is taking too long. '
                                             'Killing the script "%s"...' % (_name,))
                            process.kill()
                    except OSError:
                        pass
                    break
                util.sleep(self.TARGET_POLL_INTERVAL)
        except IOError as e:
            if e.errno != errno.EINTR:
                raise
            else:
                util.printDetail('Signal EINTR detected. Ignoring it.')
                return 0

        util.printDetail("End of the script '%s'" % (_name,))

        stderr_last_line = ''
        try:
            stderr_last_line = result.get(timeout=60)
        except Empty:
            pass
        return process.returncode, stderr_last_line

    def _write_target_script_to_file(self, target_script, name=None):
        file_suffix = ''
        if util.is_windows():
            file_suffix = '.ps1'

        directory = None
        try:
            directory = util.get_state_storage_dir()
        except Exception as e:
            util.printError('Creating script storage directory failed with: "%s"' % (e,))

        if name is None or directory is None:
            fn = tempfile.mktemp(suffix=file_suffix, dir=directory)
        else:
            filename = re.sub(r'[^0-9a-z._-]', '', name.replace('/', '_').replace(' ', '-').replace(':', '__').lower())
            if file_suffix:
                filename += file_suffix
            fn = os.path.join(directory, filename)

        if isinstance(target_script, unicode):
            with codecs.open(fn, 'w', 'utf8') as fh:
                fh.write(target_script)
        else:
            with open(fn, 'w') as fh:
                fh.write(target_script)

        os.chmod(fn, 0755)
        return fn

    def _launch_process(self, target_script, exports=None, name=None):
        '''Returns launched process as subprocess.Popen instance.
        '''

        try:
            fn = self._write_target_script_to_file(target_script, name)
        except Exception as e:
            util.printError('Writing script "%s" to file failed with: "%s". Retrying with random filename.' % (name, e))
            fn = self._write_target_script_to_file(target_script)

        current_dir = os.getcwd()
        new_dir = util.get_temporary_storage_dir()
        os.chdir(new_dir)

        if 'HOME' not in os.environ:
            if exports is None:
                exports = {}
            exports['HOME'] = os.path.expanduser('~')

        try:
            process = util.execute(fn, noWait=True, extra_env=exports, withStderr=True)
        finally:
            os.chdir(current_dir)

        return process

    def print_and_keep_last_stderr(self, stderr, result):
        last_line = None
        for line in iter(stderr.readline, b''):
            sys.stderr.write(line)
            if line.strip():
                last_line = line.strip()
        result.put(last_line)

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
                name = '_'.join(os.path.abspath(element).strip(os.sep).split(os.sep))
                archive.add(os.path.expandvars(element), name)
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

    def get_cloud_service_name(self):
        return self.wrapper._get_cloud_service_name()

    def _get_node_instance(self):
        return self.wrapper.get_my_node_instance()

    def _get_node_instance_name(self):
        return self.wrapper.get_my_node_instance_name()

    def _killItself(self, is_build_image=False):
        self.wrapper.stopOrchestrator(is_build_image)

    def _set_state_start_time(self):
        self.wrapper.set_state_start_time()

    def _log_and_set_statecustom(self, msg):
        self.wrapper._log_and_set_statecustom(msg)


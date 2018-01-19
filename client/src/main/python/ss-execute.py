#!/usr/bin/env python
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
from __future__ import print_function

import os
import sys
import time
import traceback

from slipstream.command.CommandBase import CommandBase
from slipstream.ConfigHolder import ConfigHolder
from slipstream.Client import Client
from slipstream.exceptions.Exceptions import AbortException, TimeoutException
from slipstream.resources.reports import ReportsGetter
import slipstream.util as util
from slipstream.resources.run import (run_url_to_uuid, run_states_after,
                                      RUN_STATES, FINAL_STATES)

RC_SUCCESS = 0
RC_CRITICAL_DEFAULT = 1
RC_CRITICAL_NAGIOS = 2


def print_step(msg):
    print("::: %s" % msg)


class MainProgram(CommandBase):
    '''A command-line program to execute a run of creating a new machine.'''

    RUN_TYPE = 'type'
    BYPASS_SSH_CHECK = 'bypass-ssh-check'
    REF_QNAME = util.RUN_PARAM_REFQNAME
    RUN_LAUNCH_NOT_NODE_PARAMS = (RUN_TYPE,
                                  BYPASS_SSH_CHECK,
                                  util.RUN_PARAM_REFQNAME,
                                  util.RUN_PARAM_MUTABLE,
                                  util.RUN_PARAM_KEEP_RUNNING,
                                  util.RUN_PARAM_TAGS)
    DEAFULT_WAIT = 0  # minutes
    DEFAULT_SLEEP = 30  # seconds
    INITIAL_SLEEP = 10  # seconds
    INITIAL_STATE = RUN_STATES[0]
    FINAL_STATES = FINAL_STATES

    def __init__(self, argv=None):
        self.moduleUri = None
        self.endpoint = None
        self.parameters = {}
        super(MainProgram, self).__init__(argv)

    def parse(self):
        usage = '''usage: %prog [options] <module-url>

<module-uri>    Full URL to the module to execute.
                For example Public/Tutorials/HelloWorld/client_server'''

        self.parser.usage = usage

        self.addEndpointOption()

        self.parser.add_option('--parameters', dest='parameters',
                               help='Deployment or image parameters override. '
                                    'The key must be in a form: '
                                    '<node-name>:<parameter-name> (for deployment) '
                                    'or <parameter-name> (for image). '
                                    'Several pairs can be provided comma '
                                    'separated.',
                               metavar="KEY1=VALUE1,KEY2=VALUE2",
                               default='')

        self.parser.add_option('-w', '--wait', dest='wait',
                               help='Wait MINUTES for the deployment to finish.',
                               type='int', metavar='MINUTES',
                               default=self.DEAFULT_WAIT)

        self.parser.add_option('--nagios', dest='nagios',
                               help='Behave like Nagios check.',
                               default=False, action='store_true')

        self.parser.add_option('--kill-vms-on-error',
                               dest='kill_vms_on_error',
                               help='Kill VMs on any error.',
                               default=False, action='store_true')

        self.parser.add_option('--scalable',
                               dest='scalable',
                               help='Launch a scalable application.',
                               default=False, action='store_true')

        self.parser.add_option('--check-ssh-key',
                               dest='bypass_ssh_check',
                               help="Check if there is an SSH key in the user profile",
                               default=True, action='store_false')

        self.parser.add_option('--keep-running',
                               dest='keep_running',
                               help="Define when the application should be kept running. \n" + \
                                    "Available values: never, always, on-error, on-success. \n" + \
                                    "If not set the user default will be used.",
                               default='')

        self.parser.add_option('--build-image',
                               dest='build_image',
                               help='Build the image instead of running it',
                               default=False, action='store_true')

        self.parser.add_option('--final-states', dest='final_states',
                               help='Comma separated list of final states. ' +
                                    'Default: %s' % ', '.join(self.FINAL_STATES),
                               type='string', action="callback",
                               callback=self._comma_separ_to_list_callback,
                               metavar='FINAL_STATES', default=self.FINAL_STATES)

        self.parser.add_option('--get-reports-all', dest='get_reports_all',
                               help='Get all reports after final state is reached.',
                               default=False, action='store_true')

        self.parser.add_option('--get-reports', dest='reports_components',
                               help='Comma separated list of components to download reports for. '
                                    'Example: nginx,worker.1,worker.3 - will download reports for all component '
                                    'instances of nginx and only for instances 1 and 3 of worker.',
                               type='string', action="callback",
                               callback=self._comma_separ_to_list_callback, default='')

        self.parser.add_option('--get-reports-dir', dest='output_dir',
                               help='Path to the directory to store the reports. '
                                    'Default: <working directory>/<run-uuid>.',
                               default=os.getcwd())

        self.options, self.args = self.parser.parse_args()

        self._checkArgs()

        self.resourceUrl = self.args[0]

    @staticmethod
    def _comma_separ_to_list_callback(option, opt, value, parser):
        setattr(parser.values, option.dest, value.split(','))

    def _checkArgs(self):
        if len(self.args) < 1:
            self.parser.error('Missing resource-uri')
        if len(self.args) > 1:
            self.usageExitTooManyArguments()
        self.parameters = self._parseParameters()
        if self.options.nagios:
            self.options.verboseLevel = 0

    def _parseParameters(self):
        parameters = {}
        if not self.options.parameters:
            return parameters
        for pair in self.options.parameters.split(','):
            parts = pair.split('=', 1)
            if len(parts) != 2:
                self.parser.error('Invalid parameter key/value pair: ' + pair)
            key, value = map(lambda x: x.strip(), parts)
            parameters[key] = value
        return parameters

    def doWork(self):
        self._init_client()
        run_url = self._launch_deployment()
        if self._need_to_wait():
            rc = self._get_critical_rc()
            try:
                rc = self._wait_run_and_handle_failures(run_url)
                sys.exit(rc)
            finally:
                self._cond_terminate_run(rc, run_url)
                self._download_reports(run_url)
        else:
            print(run_url)

    def _init_client(self):
        configHolder = ConfigHolder(self.options, context={'empty': None},
                                    config={'empty': None})
        configHolder.set('serviceurl', self.options.endpoint)
        self.client = Client(configHolder)

    def _launch_deployment(self):
        '''Return run URL on success.
        On failure:
        - in case of Nagios check generate CRITICAL error
        - else, the caught exception is re-raised.
        '''
        params = self._assembleData()
        try:
            return self.client.launchDeployment(params)
        except Exception as ex:
            if self.options.nagios:
                print("CRITICAL - Unhandled error: %s." % (str(ex).split('\n')[0]))
                sys.exit(RC_CRITICAL_NAGIOS)
            else:
                raise

    def _wait_run_and_handle_failures(self, run_url):
        '''Wait for final state of the run. Handle failures and print
        respective messages. Return global exit code depending if this is
        Nagios check or not.
        '''
        rc = self._get_critical_rc()

        try:
            reached_state = self._wait_run_in_states(run_url,
                                                     self.options.wait,
                                                     self.options.final_states)
        except AbortException as ex:
            if self.options.nagios:
                print('CRITICAL - %s. State: %s. Run: %s' % (
                    str(ex).split('\n')[0], ex.state, run_url))
            else:
                print('CRITICAL - %s\nState: %s. Run: %s' % (
                    str(ex), ex.state, run_url))
            ss_abort_msg = self.client.getGlobalAbortMessage()
            print('Abort reason:\n%s' % ss_abort_msg)
        except TimeoutException as ex:
            print("CRITICAL - Timed out after %i min. State: %s. Run: %s" % (
                self.options.wait, ex.state, run_url))
        except Exception as ex:
            if self.options.nagios:
                print("CRITICAL - Unhandled error: %s. Run: %s" % (
                    str(ex).split('\n')[0], run_url))
                traceback.print_exc()
            else:
                raise
        else:
            print('OK - State: %s. Run: %s' % (reached_state, run_url))
            rc = RC_SUCCESS

        return rc

    def _cond_terminate_run(self, returncode, run_url):
        """Run gets conditionally terminated
        - when we are acting as Nagios check
        - when there was a failure and we were asked to kill the VMs on error.

        Before termination, in case the abort flag was raised, we wait for reports
        uploaded from components, by waiting for any state after SendingReports.
        """

        # In case abort message is set, server-side Sate Machine will attempt
        # to advance the run through all the states up to Aborted.
        # This ensures that reports get uploaded by the components.
        if returncode != RC_SUCCESS:
            self._wait_reports_sent_if_run_aborted(run_url)

        if self.options.nagios or \
                (returncode != RC_SUCCESS and self.options.kill_vms_on_error):
            self._terminate_run()

    def _wait_reports_sent_if_run_aborted(self, run_url):
        if self._is_run_aborted(run_url):
            print_step("Abort flag was raised. Waiting for reports to be uploaded from components.")
            try:
                self._wait_run_in_states(run_url, 2, run_states_after('SendingReports'),
                                         ignore_abort=True)
            except TimeoutException:
                pass

    def _is_run_aborted(self, run_url):
        return self.client.is_run_aborted(run_url_to_uuid(run_url))

    def _terminate_run(self):
        print_step('Terminating run.')
        try:
            self.client.terminateRun()
        except:
            pass

    def _get_critical_rc(self):
        return self.options.nagios and RC_CRITICAL_NAGIOS or RC_CRITICAL_DEFAULT

    def _assembleData(self):
        self._add_not_node_params()
        return self._decorate_parameters(self.parameters,
                                         filter_out=self.RUN_LAUNCH_NOT_NODE_PARAMS)

    def _add_not_node_params(self):
        self.parameters[self.REF_QNAME] = 'module/' + self.resourceUrl

        if self.options.build_image:
            self.parameters[self.RUN_TYPE] = 'Machine'

        if self.options.scalable:
            self.parameters[util.RUN_PARAM_MUTABLE] = 'true'
            
        if self.options.bypass_ssh_check:
            self.parameters[self.BYPASS_SSH_CHECK] = 'true'
            
        if self.options.keep_running:
            self.parameters[util.RUN_PARAM_KEEP_RUNNING] = self.options.keep_running

    def _decorate_node_param_key(self, key, filter_out=[]):
        if key in filter_out:
            return key
        parts = key.split(':')
        if len(parts) == 1:
            key = parts[0]
            return 'parameter--' + key
        elif len(parts) == 2:
            nodename, key = parts
            return 'parameter--node--' + nodename + '--' + key
        else:
            self.parser.error('Invalid key format: ' + key)

    def _decorate_parameters(self, params, filter_out=[]):
        return ['%s=%s' % (self._decorate_node_param_key(k, filter_out), v)
                for k, v in params.items()]

    def _wait_run_in_states(self, run_url, waitmin, final_states, ignore_abort=False):
        '''Return on reaching one of the requested state.
        On timeout raise TimeoutException with the last state attribute set.
        On aborted Run by default raise AbortException with the last state attribute set.
        '''
        def _sleep():
            time_sleep = self.DEFAULT_SLEEP
            if _sleep.ncycle <= 2:
                if _sleep.ncycle == 1:
                    time_sleep = self.INITIAL_SLEEP
                elif _sleep.ncycle == 2:
                    time_sleep = self.DEFAULT_SLEEP - self.INITIAL_SLEEP
                _sleep.ncycle += 1
            time.sleep(time_sleep)
        _sleep.ncycle = 1

        if not self.options.nagios:
            print_step('Waiting %s min for Run %s to reach %s' % \
                       (waitmin, run_url, ','.join(final_states)))

        run_uuid = run_url_to_uuid(run_url)
        time_end = time.time() + waitmin * 60
        state = self.INITIAL_STATE
        while time.time() <= time_end:
            _sleep()
            try:
                state = self.client.getRunState(run_uuid, ignoreAbort=ignore_abort)
            except AbortException as ex:
                ex.state = self.client.getRunState(run_uuid, ignoreAbort=True)
                raise
            if state in final_states:
                return state
            if not self.options.nagios:
                curr_time = time.strftime("%Y-%M-%d-%H:%M:%S UTC", time.gmtime())
                print("[%s] State: %s" % (curr_time, state))
        time_exc = TimeoutException('Timed out.')
        time_exc.state = state
        raise time_exc

    def _need_to_wait(self):
        return self.options.wait > self.DEAFULT_WAIT

    def _download_reports(self, run_url):
        if not (self.options.reports_components or self.options.get_reports_all):
            return

        components = []
        if self.options.reports_components:
            components = self.options.reports_components
        ch = ConfigHolder(options=self.options, context={'ignore': None})
        ch.context = {}
        ch.set("session", self.client.get_session())
        rg = ReportsGetter(ch)
        rg.get_reports(run_url_to_uuid(run_url), components=components)


if __name__ == "__main__":
    try:
        MainProgram()
    except KeyboardInterrupt:
        print('\n\nExecution interrupted by the user... goodbye!')
        sys.exit(-1)

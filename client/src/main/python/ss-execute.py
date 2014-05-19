#!/usr/bin/env python
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
from __future__ import print_function

import os
import sys
import time
import traceback

from slipstream.CommandBase import CommandBase
from slipstream.ConfigHolder import ConfigHolder
from slipstream.Client import Client
from slipstream.exceptions.Exceptions import AbortException, TimeoutException
import slipstream.util as util

default_endpoint = os.environ.get('SLIPSTREAM_ENDPOINT',
                                  'http://slipstream.sixsq.com')
default_cookie = os.environ.get('SLIPSTREAM_COOKIEFILE',
                                os.path.join(util.TMPDIR, 'cookie'))

RC_SUCCESS = 0
RC_CRITICAL_DEFAULT = 1
RC_CRITICAL_NAGIOS = 2

class MainProgram(CommandBase):
    '''A command-line program to execute a run of creating a new machine.'''

    REF_QNAME = 'refqname'
    DEAFULT_WAIT = 0  # minutes
    DEFAULT_SLEEP = 30  # seconds
    INITIAL_SLEEP = 10  # seconds
    INITIAL_STATE = 'Inactive'

    def __init__(self, argv=None):
        self.moduleUri = None
        self.username = None
        self.password = None
        self.cookie = None
        self.endpoint = None
        self.parameters = {}
        super(MainProgram, self).__init__(argv)

    def parse(self):
        usage = '''usage: %prog [options] <module-url>

<module-uri>    Full URL to the module to execute.
                For example Public/Tutorials/HelloWorld/client_server'''

        self.parser.usage = usage

        self.parser.add_option('-u', '--username', dest='username',
                               help='SlipStream username', metavar='USERNAME',
                               default=os.environ.get('SLIPSTREAM_USERNAME'))
        self.parser.add_option('-p', '--password', dest='password',
                               help='SlipStream password', metavar='PASSWORD',
                               default=os.environ.get('SLIPSTREAM_PASSWORD'))

        self.parser.add_option('--cookie', dest='cookieFilename',
                               help='SlipStream cookie', metavar='FILE',
                               default=default_cookie)

        self.parser.add_option('--endpoint', dest='endpoint',
                               help='SlipStream server endpoint', metavar='URL',
                               default=default_endpoint)

        self.parser.add_option('--parameters', dest='parameters',
                               help='Deployment or image parameters override. '
                                    'The key must be in a form: '
                                    '<node-name>:<parameter-name>. '
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

        self.options, self.args = self.parser.parse_args()

        self._checkArgs()

        self.resourceUrl = self.args[0]

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
            parts = pair.split('=')
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
                self._cond_terminate_run(rc)
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
        final_states = ['Terminal', 'Detached']

        try:
            final_state = self._wait_run_in_final_state(run_url,
                                                        self.options.wait,
                                                        final_states)
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
            print('OK - State: %s. Run: %s' % (final_state, run_url))
            rc = RC_SUCCESS

        return rc

    def _cond_terminate_run(self, returncode):
        '''Run gets conditionally terminated
        - when we are acting as Nagios check
        - when there was a failure and we were asked to kill the VMs on error.
        '''
        if self.options.nagios or\
                (returncode != RC_SUCCESS and self.options.kill_vms_on_error):
            self._terminate_run()

    def _terminate_run(self):
        try:
            self.client.terminateRun()
        except:
            pass

    def _get_critical_rc(self):
        return self.options.nagios and RC_CRITICAL_NAGIOS or RC_CRITICAL_DEFAULT

    def _assembleData(self):
        self.parameters[self.REF_QNAME] = 'module/' + self.resourceUrl
        return [self._decorateKey(k) + '=' + v for k, v in self.parameters.items()]

    def _decorateKey(self, key):
        if key == self.REF_QNAME:
            return key
        parts = key.split(':')
        if len(parts) != 2:
            self.parser.error('Invalid key format: ' + key)
        nodename, key = parts
        return 'parameter--node--' + nodename + '--' + key

    def _wait_run_in_final_state(self, run_url, waitmin, final_states):
        '''Return on reaching final state.
        On timeout raise TimeoutException with the last state attribute set.
        On aborted Run raise AbortException with the last state attribute set.
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

        run_uuid = run_url.rsplit('/', 1)[-1]
        time_end = time.time() + waitmin * 60
        state = self.INITIAL_STATE
        while time.time() <= time_end:
            _sleep()
            try:
                state = self.client.getRunState(run_uuid, ignoreAbort=False)
            except AbortException as ex:
                ex.state = state
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

if __name__ == "__main__":
    try:
        MainProgram()
    except KeyboardInterrupt:
        print('\n\nExecution interrupted by the user... goodbye!')
        sys.exit(-1)

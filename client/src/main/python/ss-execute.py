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

from slipstream.CommandBase import CommandBase
from slipstream.ConfigHolder import ConfigHolder
from slipstream.Client import Client
from slipstream.exceptions import Exceptions
import slipstream.util as util

default_endpoint = os.environ.get('SLIPSTREAM_ENDPOINT',
                                  'http://slipstream.sixsq.com')
default_cookie = os.environ.get('SLIPSTREAM_COOKIEFILE',
                                os.path.join(util.TMPDIR, 'cookie'))


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

    def _init_client(self):
        configHolder = ConfigHolder(self.options, context={'empty': None},
                                    config={'empty': None})
        configHolder.set('serviceurl', self.options.endpoint)
        self.client = Client(configHolder)

    def _launch_deployment(self):
        params = self._assembleData()
        return self.client.launchDeployment(params)

    def doWork(self):
        self._init_client()
        run_url = self._launch_deployment()
        if self._need_to_wait():
            self._wait_run_in_final_state(run_url)
        else:
            print(run_url)

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

    def _wait_run_in_final_state(self, run_url):
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
        time_end = time.time() + self.options.wait * 60
        state = self.INITIAL_STATE
        CRITICAL = self.options.nagios and 2 or 1
        while time.time() <= time_end:
            _sleep()
            try:
                state = self.client.getRunState(run_uuid, ignoreAbort=False)
            except Exceptions.AbortException as ex:
                if self.options.nagios:
                    print('CRITICAL - %s. State: %s. Run: %s' % (
                        str(ex).split('\n')[0], state, run_url))
                    sys.exit(CRITICAL)
                else:
                    raise ex
            if state == 'Terminal':
                print('OK - Terminal. Run: %s' % run_url)
                sys.exit(0)
            curr_time = time.strftime("%Y-%M-%d-%H:%M:%S UTC", time.gmtime())
            if not self.options.nagios:
                print("[%s] State: %s" % (curr_time, state))
        print("CRITICAL - Timed out after %i min. State: %s. Run: %s" % (
            self.options.wait, state, run_url))
        sys.exit(CRITICAL)

    def _need_to_wait(self):
        return self.options.wait > self.DEAFULT_WAIT

if __name__ == "__main__":
    try:
        MainProgram()
    except KeyboardInterrupt:
        print('\n\nExecution interrupted by the user... goodbye!')
        sys.exit(-1)

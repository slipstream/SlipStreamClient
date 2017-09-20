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

import sys

from slipstream.command.DeploymentCommandBase import DeploymentCommandBase


class MainProgram(DeploymentCommandBase):
    """A command-line program to get a runtime parameter value from a run,
    blocking (by default) if not set.
    """

    def __init__(self):
        super(MainProgram, self).__init__()
        self.key = None

    def parse(self):
        usage = '''usage: %prog [options] <name>

<name>   Name of the deployment parameter from which to retrieve the value
         The interpretation of the <name> is as follows: 
         name - parameter of this component
         ss:name - global parameter (`ss` special namespace)
         node.1:name - single parameter
         node:name - parameter values of all the active instances of the `node` 
                      node.1:name value
                      node.2:name value
         '''

        self.parser.usage = usage

        self.parser.add_option('--timeout', dest='timeout',
                               help='timeout in seconds for blocking call',
                               metavar='SECONDS',
                               default=60, type='int')

        self.add_ignore_abort_option()

        self.parser.add_option('--noblock', dest='no_block',
                               help='return immediately even if the parameter '
                                    'has no value',
                               default=False, action='store_true')

        self.add_run_authn_opts_and_parse()

        self._check_args()

        self.key = self.args[0]

    def _check_args(self):
        if len(self.args) < 1:
            self.parser.error('Missing key')
        if len(self.args) > 1:
            self.usageExitTooManyArguments()

    def do_work(self):
        res = self.get_deployment_parameter(self.key)

        def get_value(param):
            return param.get('value', '')

        def get_full_key(param):
            node = param.get('node-name')
            index = param.get('node-index', None)
            name = param.get('name')
            if index:
                return '{}.{}:{}'.format(node, index, name)
            else:
                return '{}:{}'.format(node, name)

        if isinstance(res, list):
            for p in res:
                print('{} {}'.format(get_full_key(p), get_value(p)))
        else:
            print(get_value(res))


if __name__ == "__main__":
    try:
        MainProgram()
    except KeyboardInterrupt:
        print('\n\nExecution interrupted by the user... goodbye!')
        sys.exit(-1)

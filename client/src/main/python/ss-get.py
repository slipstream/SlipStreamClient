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

from slipstream.command.VMCommandBase import VMCommandBase
from slipstream.api.deployment import Deployment


class MainProgram(VMCommandBase):
    """A command-line program to get a runtime parameter value from a run,
    blocking (by default) if not set.
    """

    def __init__(self):
        self._dpl = None
        super(MainProgram, self).__init__()
        self.key = None

    def parse(self):
        usage = '''usage: %prog [options] <key>

<key>    Key (i.e. runtime parameter) from which to retrieve the value'''

        self.parser.usage = usage

        self.parser.add_option('--timeout', dest='timeout',
                               help='timeout in seconds for blocking call',
                               metavar='SECONDS',
                               default=60, type='int')

        self.addIgnoreAbortOption()

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

    @property
    def deployment(self):
        if not self._dpl:
            self._dpl = Deployment(self.cimi, self.options.diid)
        return self._dpl

    def do_work(self):
        comp, _id, name = self._split_key(self.key)
        if _id:
            value = self.deployment.get_deployment_parameter(comp, _id, name)
        else:
            value = self.deployment.get_deployment_parameters(comp, name)
        print(value if value is not None else '')

    def _split_key(self, key):
        name = key
        _id = None
        if ':' in key:
            comp_id, name = key.split(':')
        else:
            return None, None, name
        if '.' in comp_id:
            comp, _id = comp_id.split('.')
        else:
            comp = comp_id
        return comp, _id, name


if __name__ == "__main__":
    try:
        MainProgram()
    except KeyboardInterrupt:
        print('\n\nExecution interrupted by the user... goodbye!')
        sys.exit(-1)

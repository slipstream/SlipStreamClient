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

from slipstream.Client import Client
from slipstream.ConfigHolder import ConfigHolder
from slipstream.command.CommandBase import CommandBase


class MainProgram(CommandBase):
    """
    A command-line program to get a runtime parameter value from a run,
    blocking (by default) if not set.
    """

    def __init__(self, argv=None):
        super(MainProgram, self).__init__(argv)
        self.compname = None
        self.key = None

    def parse(self):
        usage = """usage: %prog [options] <component> <key>

<component> Name of the component.
<key>       Key (non-qualified runtime parameter) to retrieve the value from
"""

        self.parser.usage = usage

        self.parser.add_option('--timeout', dest='timeout',
                               help='timeout in seconds for blocking call',
                               metavar='SECONDS',
                               default=60, type='int')

        self.addIgnoreAbortOption()

        self.parser.add_option('--noblock', dest='noBlock',
                               help='return immediately even if the parameter '
                                    'has no value',
                               default=False, action='store_true')

        self.options, self.args = self.parser.parse_args()

        self._check_args()
        self.compname = self.args[0]
        self.key = self.args[1]

    def _check_args(self):
        if len(self.args) < 1:
            self.parser.error('Missing component name and key')
        if len(self.args) < 2:
            self.parser.error('Missing key')
        if len(self.args) > 2:
            self.usageExitTooManyArguments()

    def _get_client(self):
        configHolder = ConfigHolder(self.options)
        return Client(configHolder)

    def doWork(self):
        client = self._get_client()
        params = client.get_rtp_all(self.compname, self.key)
        for k, v in params:
            print(k, v)


if __name__ == "__main__":
    try:
        MainProgram()
    except KeyboardInterrupt:
        print('\n\nExecution interrupted by the user... goodbye!')
        sys.exit(-1)

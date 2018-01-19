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
import os

from slipstream.command.CommandBase import CommandBase
from slipstream.Client import Client
from slipstream.ConfigHolder import ConfigHolder


class MainProgram(CommandBase):
    """A command-line program to login to SlipStream.  Expects username and
    password on input, authenticates with SlipStream and stores the cookie in
    the local cookie store.
    """

    def __init__(self, argv=None):
        self.username = None
        self.password = None
        super(MainProgram, self).__init__(argv)

    def add_authentication_options(self):
        self.parser.add_option('-u', '--username', dest='username',
                               help='SlipStream username or $SLIPSTREAM_USERNAME',
                               metavar='USERNAME',
                               default=os.environ.get('SLIPSTREAM_USERNAME'))
        self.parser.add_option('-p', '--password', dest='password',
                               help='SlipStream password or $SLIPSTREAM_PASSWORD',
                               metavar='PASSWORD',
                               default=os.environ.get('SLIPSTREAM_PASSWORD'))

    def parse(self):
        usage = """usage: %prog [options]"""

        self.parser.usage = usage

        self.addEndpointOption()
        self.add_authentication_options()

        self.options, self.args = self.parser.parse_args()

        self.options.serviceurl = self.options.endpoint
        self.username = self.options.username
        self.options.username = None
        self.password = self.options.password
        self.options.password = None

        self._check_args()

    def _check_args(self):
        if len(self.args) > 0:
            self.usageExitTooManyArguments()

    def doWork(self):
        ch = ConfigHolder(self.options, context={'empty': None}, config={'empty': None})
        ch.set('serviceurl', self.options.endpoint)
        client = Client(ch)
        client.login(self.username, self.password)


if __name__ == "__main__":
    try:
        MainProgram()
    except KeyboardInterrupt:
        print('\n\nExecution interrupted by the user... goodbye!')
        sys.exit(-1)

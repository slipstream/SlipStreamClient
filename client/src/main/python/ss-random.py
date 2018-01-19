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
import random
import string

from slipstream.command.VMCommandBase import VMCommandBase
from slipstream.Client import Client
from slipstream.ConfigHolder import ConfigHolder


class MainProgram(VMCommandBase):
    """A command-line program to generate random string (e.g. for password)
    and optionally set it in a runtime parameter.
    """

    def __init__(self, argv=None):
        self.key = None
        self.size = None
        self.endpoint = None
        super(MainProgram, self).__init__(argv)

    def parse(self):
        usage = '''usage: %prog [options] [<key>]

<key>   Key for which to set the random value. If not provided, the random
        value is only returned.'''

        self.parser.usage = usage
        self.parser.add_option('-s', '--size', dest='size', metavar='NUMBER',
                               help='Number of characters for the random ' +
                               'string (default: 12)', default=12)

        self.add_run_opts_and_parse()

        self._check_args()

    def _check_args(self):
        if len(self.args) > 1:
            self.usageExitTooManyArguments()
        if len(self.args) == 1:
            self.key = self.args[0]
        try:
            self.size = int(self.options.size)
            if self.size < 1:
                self.usageExit('Size value must be a positive integer')
        except ValueError:
            self.usageExit("Invalid size value, must be a positive integer")

    def doWork(self):

        rvalue = ''.join([random.choice(string.ascii_letters + string.digits)
                          for _ in xrange(self.size)])

        if self.key is not None:
            ch = ConfigHolder(self.options)
            client = Client(ch)
            client.setRuntimeParameter(self.key, rvalue)

        print(rvalue)

if __name__ == "__main__":
    try:
        MainProgram()
    except KeyboardInterrupt:
        print('\n\nExecution interrupted by the user... goodbye!')
        sys.exit(-1)

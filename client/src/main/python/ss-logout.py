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
from slipstream.Client import Client
from slipstream.ConfigHolder import ConfigHolder


class MainProgram(VMCommandBase):
    """A command-line program to logout from SlipStream.  It deletes the local
    cookie corresponding to <endpoint>/ resource.
    """

    def __init__(self, argv=None):
        super(MainProgram, self).__init__(argv)

    def parse(self):
        usage = """usage: %prog [options]
 
Deletes cookie for / of <URL> from local cookie jar <FILE>."""

        self.parser.usage = usage

        self.addEndpointOption()

        self.options, self.args = self.parser.parse_args()

        self.options.serviceurl = self.options.endpoint

        self._check_args()

    def _check_args(self):
        if len(self.args) > 0:
            self.usageExitTooManyArguments()

    def doWork(self):
        ch = ConfigHolder(self.options)
        client = Client(ch)
        client.logout()


if __name__ == "__main__":
    try:
        MainProgram()
    except KeyboardInterrupt:
        print('\n\nExecution interrupted by the user... goodbye!')
        sys.exit(-1)

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
    """A command-line program to set directly the statecustom value, such that
    the dashboard can be made more dynamic.
    """

    def __init__(self, argv=None):
        self.value = None
        super(MainProgram, self).__init__(argv)

    def parse(self):
        usage = '''%prog [options] [--] <value>

<value>          Value to be set.

Notice:
                 If the value might start with a dash (-), please add the two
                 dashes (--) before the value to prevent possible issues.'''

        self.parser.usage = usage

        self.addIgnoreAbortOption()

        self.add_run_opts_and_parse()

        if len(self.args) != 1:
                self.usageExit('Error, one argument must be specified')

        self.value = self.args[0]

    def doWork(self):
        ch = ConfigHolder(self.options)
        client = Client(ch)
        client.setRuntimeParameter('statecustom', self.value)

if __name__ == "__main__":
    try:
        MainProgram()
    except KeyboardInterrupt:
        print('\n\nExecution interrupted by the user... goodbye!')
        sys.exit(-1)

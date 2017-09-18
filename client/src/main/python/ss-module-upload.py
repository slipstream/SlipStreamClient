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

from slipstream.command.ModuleCommand import ModuleCommand


class MainProgram(ModuleCommand):
    """Uploads a collection of modules (in XML format) to the server."""

    def __init__(self):
        super(MainProgram, self).__init__()

    def parse(self):
        usage = '''usage: %prog [options] <file> ...'''

        self.parser.usage = usage
        self.add_authentication_options()
        self.add_endpoint_option()

        self.parser.add_option('-f', '--force', dest='force',
                               help='Force execution, ignoring errors',
                               default=False, action='store_true')

        self.options, self.args = self.parser.parse_args()

        self._check_args()

    def _check_args(self):
        if len(self.args) == 0:
            self.usageExit("You must provide at least one file to upload.")
        self.force = self.options.force

    def do_work(self):
        self.modules_upload()


if __name__ == "__main__":
    try:
        MainProgram()
    except KeyboardInterrupt:
        print('\n\nExecution interrupted by the user... goodbye!')
        sys.exit(-1)

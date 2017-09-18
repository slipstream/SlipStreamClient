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
    """A command-line program to delete module definition(s)."""

    def __init__(self):
        super(MainProgram, self).__init__()

    def parse(self):
        usage = '''usage: %prog [options] [<module-uri>]

<module-uri>    Name of the module to delete. For example
                Public/Tutorials/HelloWorld/client_server/1. If a version
                is provided (at the end of the module name) this specific
                version will be deleted, otherwise the last version will
                be deleted.  If several versions exists, this command must
                be called repeatedly.'''

        self.parser.usage = usage
        self.add_authentication_options()
        self.add_endpoint_option()

        self.options, self.args = self.parser.parse_args()
        
        self._check_args()

    def _check_args(self):
        if len(self.args) == 1:
            self.module_uri = self.args[0]
        if len(self.args) < 1:
            self.usageExitTooFewArguments()
        if len(self.args) > 1:
            self.usageExitTooManyArguments()

    def do_work(self):
        self.module_delete(self.module_uri)


if __name__ == "__main__":
    try:
        MainProgram()
    except KeyboardInterrupt:
        print('\n\nExecution interrupted by the user... goodbye!')
        sys.exit(-1)

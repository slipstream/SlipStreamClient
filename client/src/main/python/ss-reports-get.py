#!/usr/bin/env python
"""
 SlipStream Client
 =====
 Copyright (C) 2016 SixSq Sarl (sixsq.com)
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

from slipstream.command.CommandBase import CommandBase
from slipstream.ConfigHolder import ConfigHolder
from slipstream.api.reports import ReportsGetter


class MainProgram(CommandBase):
    """A command-line program to download deployment reports."""

    def __init__(self):
        self.module = ''
        self.username = None
        self.password = None
        self.cookie = None
        self.endpoint = None
        super(MainProgram, self).__init__()

    def parse(self):
        usage = '''usage: %prog [options] [<run-uuid>]

<run-uuid>    UUID of the run to get reports from.'''

        self.parser.usage = usage
        self.add_authentication_options()
        self.add_endpoint_option()

        self.parser.add_option('-c', '--components', dest='components',
                               help='Comma separated list of components to download the reports for. '
                                    'Example: nginx,worker.1,worker.3 - will download reports for all component '
                                    'instances of nginx and only for instances 1 and 3 of worker. '
                                    'Default: all instances of all components.', default='')

        self.parser.add_option('-o', '--output-dir', dest='output_dir',
                               help='Path to the directory to store the reports. Default: <working directory>/<run-uuid>.',
                               default=os.getcwd())

        self.parser.add_option('--no-orch', dest='no_orch',
                               help='Do not download Orchestrator report.',
                               default=False, action='store_true')

        self.options, self.args = self.parser.parse_args()

        if self.options.components:
            self.options.components = self.options.components.split(',')
        else:
            self.options.components = []

        self._checkArgs()

    def _checkArgs(self):
        if len(self.args) == 1:
            self.run_uuid = self.args[0]
        if len(self.args) > 1:
            self.usageExitTooManyArguments()

    def do_work(self):
        ch = ConfigHolder(options=self.options, context={})
        ch.context = {}
        rg = ReportsGetter(ch)
        rg.get_reports(self.run_uuid, components=self.options.components,
                       no_orch=self.options.no_orch)


if __name__ == "__main__":
    try:
        MainProgram()
    except KeyboardInterrupt:
        print('\n\nExecution interrupted by the user... goodbye!')
        sys.exit(-1)

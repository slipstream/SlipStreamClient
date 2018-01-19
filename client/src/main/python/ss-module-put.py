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

import os
import sys

from slipstream.command.CommandBase import CommandBase
from slipstream.HttpClient import HttpClient
import slipstream.util as util
import slipstream.SlipStreamHttpClient as SlipStreamHttpClient

class MainProgram(CommandBase):
    '''A command-line program to show/list module definition(s).'''

    def __init__(self, argv=None):
        self.module = ''
        self.endpoint = None
        super(MainProgram, self).__init__(argv)

    def parse(self):
        usage = '''usage: %prog [options] [<module-xml>]

<module-xml>    XML rendering of the module to update (e.g. as produced by
                ss-module-get).
                For example: ./ss-module-put "`cat module.xml`"'''

        self.parser.usage = usage

        self.addEndpointOption()        

        self.parser.add_option('-i', '--ifile', dest='ifile', metavar='FILE',
                               help='Optional input file. '
                                    'Replaces <module-xml> argument')

        self.options, self.args = self.parser.parse_args()

        self._checkArgs()

    def _checkArgs(self):
        if self.options.ifile:
            file = self.options.ifile
        else:
            if len(self.args) < 1:
                self.parser.error('Missing module-xml')
            if len(self.args) > 1:
                self.usageExitTooManyArguments()
            file = self.args[0]
        self.module = self.read_input_file(file)

    def doWork(self):
        client = HttpClient()
        client.verboseLevel = self.verboseLevel

        dom = self.read_xml_and_exit_on_error(self.module)
        attrs = SlipStreamHttpClient.DomExtractor.get_attributes(dom)

        root_node_name = dom.tag
        if root_node_name == 'list':
            sys.stderr.write('Cannot update root project\n')
            sys.exit(-1)
        if not dom.tag in ('imageModule', 'projectModule', 'deploymentModule'):
            sys.stderr.write('Invalid xml\n')
            sys.exit(-1)

        parts = [attrs['parentUri'], attrs['shortName']]
        uri = '/' + '/'.join([part.strip('/') for part in parts])

        url = self.options.endpoint + uri

        client.put(url, self.module)

if __name__ == "__main__":
    try:
        MainProgram()
    except KeyboardInterrupt:
        print('\n\nExecution interrupted by the user... goodbye!')
        sys.exit(-1)

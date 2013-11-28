#!/usr/bin/env python
"""
 SlipStream Client
 =====
 Copyright (C) 2013 SixSq Sarl (sixsq.com)
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

import sys
import getopt

import CommandBase
from slipstream import RestClient
import slipstream.exceptions.Exceptions as Exceptions
from slipstream import LocalRuntimeConnector


class MainProgram(CommandBase.CommandBase):
    ''' Trigger execution or build on SlipStream server.'''

    USAGE = '''\
Usage: %(progName)s <module> <username> <password>

<module>         Module to execute or build
<username>       Valid SlipStream standard username
<password>       Corresponding SlipStream password

options:
  --quiet        Only prints minimum information
  --verbose      Prints additional information (default)
  -h, --help     Show this message
'''

    def __init__(self, argv=None):
        self.module = None
        self.username = None
        self.password = None
        self.timeout = 30 * 60  # 30 minutes
        super(MainProgram, self).__init__(argv)

    def parseArgs(self, argv):
        try:
            options, args = getopt.getopt(argv[1:], 'h',
                                          ['help', 'quiet',
                                           'verbose', 'help'])
        except getopt.GetoptError as err:
            msg = err.__str__()
            self.usageExit(msg)
        for opt, value in options:
            if opt in ('--verbose',):
                self.verbose = True
        if len(args) < 3:
            self.usageExit('Error, missing argument(s)')
        if len(args) > 3:
            self.usageExit('Error, too many arguments')
        self.module = args[0]
        self.username = args[1]
        self.password = args[2]
        return

    def doWork(self):
        LocalRuntimeConnector.LocalRuntimeConnector.instanceDataDict = {}
        cloudConnectorModules = {'runtime': 'slipstream.LocalRuntimeConnector'}
        client = RestClient.RestClient(self.verbose, cloudConnectorModules)
        print >> sys.stderr, 'Executing/building module:', self.module
        try:
            uuid = client.submit(self.module, self.username, self.password)
        except Exceptions.ClientError as ex:
            print 'Client error: %s' % ex
            sys.exit(-1)
        print >> sys.stderr, 'Submitted with execution id:'
        print uuid
        return

main = MainProgram

##############################################################################
# Executing this module from the command line
##############################################################################

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print '\n\nExecution interrupted by the user... goodbye!'

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
import slipstream.commands.NodeInstanceRuntimeParameter as NodeInstanceRuntimeParameter

class MainProgram(CommandBase):
    '''A command-line program to remove node instance(s) from a scalable deployment.'''

    def __init__(self, argv=None):
        self.runId = None
        self.nodeName = None
        self.instancesToRemove = []

        self.endpoint = None
        super(MainProgram, self).__init__(argv)

    def parse(self):
        usage = '''usage: %prog [options] <run> <node-name> <ids> [<ids> ...]

<run>        Run id of the scalable deployment from which to remove instance(s).
<node-name>  Node name to remove instances from.
<ids>        Ids of the node instances to to remove from a scalable deployment run.'''

        self.parser.usage = usage
        self.addEndpointOption()

        self.options, self.args = self.parser.parse_args()
        self._check_args()

    def _check_args(self):
        if len(self.args) < 3:
            self.usageExitTooFewArguments()
        self.runId = self.args[0]
        self.nodeName = self.args[1]
        instancesToRemove = self.args[2:]

        try:
            self.instancesToRemove = map(int, instancesToRemove)
        except ValueError:
            self.usageExit("Invalid ids, they must be integers")


    def doWork(self):

        client = HttpClient()
        client.verboseLevel = self.verboseLevel

        uri = util.RUN_RESOURCE_PATH + "/" + self.runId + "/" + self.nodeName
        url = self.options.endpoint + uri

        instances = str(self.instancesToRemove)[1:-1]
        self.log("Removing node instances: %s..." % instances)

        print(instances)
        client.delete(url, "ids=" + instances)


if __name__ == "__main__":
    try:
        MainProgram()
    except KeyboardInterrupt:
        print('\n\nExecution interrupted by the user... goodbye!')
        sys.exit(-1)

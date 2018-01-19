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
from slipstream.NodeDecorator import NodeDecorator

class MainProgram(CommandBase):
    '''A command-line program to add node instance(s) to a scalable deployment.'''

    def __init__(self, argv=None):
        self.runId = None
        self.nodeName = None
        self.numberToAdd = 1
        self.numberToTolerate = 0
        self.runtimeParameters = []

        self.endpoint = None
        super(MainProgram, self).__init__(argv)

    def parse(self):
        usage = '''usage: %prog [options] <run> <node-name> [<number>]

<run>        Run id of the scalable deployment to which to add instance(s).
<node-name>  Node name to add instances to.
<number>     Number of node instances to add to the scalable deployment run.
             By default, add one.

<number-tolerate>   Max number of failed instances to tolerate.
             By default, 0. The value should be less than <number>.'''

        self.parser.usage = usage
        self.addEndpointOption()
        self.parser.add_option('--runtime-parameter',
                               dest='runtimeParameters',
                               metavar='<parameter-name>:<value>[,<value>,...]',
                               help='Where values are a comma separated list of values, '
                                    'each assigned to the corresponding node instance '
                                    'runtime parameter.',
                               action='append',
                               default=[])

        self.options, self.args = self.parser.parse_args()
        self._check_args()

    def _check_args(self):
        if len(self.args) < 2:
            self.usageExitTooFewArguments()
        if len(self.args) > 4:
            self.usageExitTooManyArguments()
        if len(self.args) >= 3:
            self.numberToAdd = int(self.args[2])
        if len(self.args) == 4:
            self.numberToTolerate = int(self.args[3])
            if self.numberToTolerate >= self.numberToAdd:
                self.usageExit("Number of failed instances to tolerate should be less than "
                               "the number of instances to add.")
        self.runId = self.args[0]
        self.nodeName = self.args[1]

        self.runtimeParameters = self.options.runtimeParameters
        for rp in self.runtimeParameters:
            NodeInstanceRuntimeParameter.validate(rp)

    def doWork(self):

        client = HttpClient()
        client.verboseLevel = self.verboseLevel

        baseUri = util.RUN_RESOURCE_PATH + "/" + self.runId
        nodeUri = baseUri + "/" + self.nodeName
        url = self.options.endpoint + nodeUri

        self.log("Adding %s node instance(s) to node type %s..." % (self.numberToAdd, self.nodeName))
        _, content = client.post(url, "n=" + str(self.numberToAdd))

        addedIds = NodeInstanceRuntimeParameter.parse_added_node_instances(content)

        url = self.options.endpoint + baseUri + '/'

        if self.numberToTolerate > 0:
            self.log("Setting max-provisioning-failures to %s on node %s..." %
                     (self.numberToTolerate, self.nodeName))
            runtime_param = self.nodeName + NodeDecorator.NODE_PROPERTY_SEPARATOR + \
                            NodeDecorator.MAX_PROVISIONING_FAILURES_KEY
            client.put(url + runtime_param, str(self.numberToTolerate))

        if self.runtimeParameters:
            for rp in self.runtimeParameters:
                name, values = NodeInstanceRuntimeParameter.parse_option_value(rp)
                mapped = NodeInstanceRuntimeParameter.generate_mapping_index_name_value(self.nodeName, name, values, addedIds)
                for k in mapped:
                    print(k, mapped[k])
                    client.put(url + k, mapped[k])


if __name__ == "__main__":
    try:
        MainProgram()
    except KeyboardInterrupt:
        print('\n\nExecution interrupted by the user... goodbye!')
        sys.exit(-1)

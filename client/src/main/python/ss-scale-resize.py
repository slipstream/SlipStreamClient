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
from slipstream.wrappers.BaseWrapper import BaseWrapper
from slipstream.command.VerticalScaleCommandBase import VerticalScaleCommandBase


class MainProgram(VerticalScaleCommandBase):


    def __init__(self, argv=None):
        self._usage_options = "[options] [--cpu <num>, --ram <num>]|[--instance-type <type>] <run> <node-name> <ids> [<ids> ...]"
        super(MainProgram, self).__init__(argv)

    def add_scale_options(self):
        self.parser.add_option('--cpu', dest='cpu', default=None,
                               help='New number of CPUs.', metavar='CPU')
        self.parser.add_option('--ram', dest='ram', default=None,
                               help='New number of RAM (GB).', metavar='RAM')
        self.parser.add_option('--instance-type', dest='instance_type', default=None,
                               help='New instance type.', metavar='INSTANCETYPE')

    def _validate_and_set_scale_options(self):
        if not any([self.options.cpu, self.options.ram, self.options.instance_type]):
            self.usageExit("CPU/RAM or instance type should be defined. "
                           "Make sure cloud supports either of those.")
        if any([self.options.cpu, self.options.ram]) and self.options.instance_type:
            self.usageExit("Either CPU/RAM or instance type must be provided.")

        self._scale_state = BaseWrapper.SCALE_STATE_RESIZING

        if self.options.cpu:
            self.rtp_scale_values['cpu'] = self.options.cpu
        if self.options.ram:
            self.rtp_scale_values['ram'] = self.options.ram
        if self.rtp_scale_values:
            return

        self.rtp_scale_values['instance.type'] = self.options.instance_type

    def doWork(self):
        super(MainProgram, self).doWork()
        print('Requested resizing of %s' % self.node_name)


if __name__ == "__main__":
    try:
        MainProgram()
    except KeyboardInterrupt:
        print('\n\nExecution interrupted by the user... goodbye!')
        sys.exit(-1)

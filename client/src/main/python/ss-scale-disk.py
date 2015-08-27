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
from slipstream.command.VerticalScaleCommandBase import VerticalScaleCommandBase
from slipstream.wrappers.BaseWrapper import BaseWrapper


class MainProgram(VerticalScaleCommandBase):


    def __init__(self, argv=None):
        self._usage_options = "[options] [--attach <GB> | --detach <device>] <run> <node-name> <ids> [<ids> ...]"
        super(MainProgram, self).__init__(argv)

    def add_scale_options(self):
        self.parser.add_option('--attach', dest='attach_gb', default=None,
                               help='New extra disk to attach in GB.', metavar='ATTACH_GB')
        self.parser.add_option('--detach', dest='device', default=None,
                               help='Device name to detach. (Example: /dev/vdc)', metavar='DEVICE')

    def _validate_and_set_scale_options(self):
        if not any([self.options.attach_gb, self.options.device]):
            self.usageExit("Either --attach or --detach should be provided")

        self._need_cloudservice_name = False

        if self.options.attach_gb:
            self.rtp_scale_values['disk.attach.size'] = self.options.attach_gb
            self._scale_state = BaseWrapper.SCALE_STATE_DISK_ATTACHING
            return

        if self.options.device:
            self.rtp_scale_values['disk.detach.device'] = self.options.device
            self._scale_state = BaseWrapper.SCALE_STATE_DISK_DETACHING

    def doWork(self):
        super(MainProgram, self).doWork()
        action = self.options.attach_gb and 'attach' or 'detach'
        print('Requested %sment of extra disk on %s' % (action, self.node_name))

if __name__ == "__main__":
    try:
        MainProgram()
    except KeyboardInterrupt:
        print('\n\nExecution interrupted by the user... goodbye!')
        sys.exit(-1)

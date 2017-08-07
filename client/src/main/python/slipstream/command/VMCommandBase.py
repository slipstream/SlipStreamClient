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

from slipstream.command.CommandBase import CommandBase


class VMCommandBase(CommandBase):

    def __init__(self, argv=None):
        super(VMCommandBase, self).__init__(argv)

    def add_run_authn_opts_and_parse(self):
        self.parser.add_option('--run', dest='diid', help='Run UUID.',
                               metavar='UUID', default='')
        self.addEndpointOption()
        self.add_authentication_options()

        self.options, self.args = self.parser.parse_args()

        self.options.serviceurl = self.options.endpoint
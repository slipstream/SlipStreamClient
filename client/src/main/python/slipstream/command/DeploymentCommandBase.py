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

from slipstream.api.deployment import Deployment, is_global_ns
from slipstream.command.CommandBase import CommandBase


def split_key(key):
    """`key` is [node[.id]:]name, i.e. one of
    name - parameter of the current component
    node:name - parameter of all active components
    ss:name - global parameter
    node.id:name - parameter of the specific instance of the component

    :param key: Deployment parameter
    :type  key: str
    :return: Three-tuple with comp, id, and name
    :rtype: (str, str, str)
    """
    name = key
    _id = None
    if ':' in key:
        comp_id, name = key.split(':')
    else:
        return None, None, name
    if '.' in comp_id:
        comp, _id = comp_id.split('.')
    else:
        comp = comp_id
    return comp, _id, name


class DeploymentCommandBase(CommandBase):

    def __init__(self):
        self._dpl = None
        super(DeploymentCommandBase, self).__init__()

    def add_run_authn_opts_and_parse(self):
        self.parser.add_option('--run', dest='diid', help='Run UUID.',
                               metavar='UUID', default='')
        self.add_endpoint_option()
        self.add_authentication_options()

        self.options, self.args = self.parser.parse_args()

        self.options.serviceurl = self.options.endpoint

    @property
    def deployment(self):
        if not self._dpl:
            self._dpl = Deployment(self.cimi, self.options.diid)
        return self._dpl

    def get_deployment_parameter(self, key):
        comp, _id, name = split_key(key)
        return self.deployment.get_deployment_parameter(comp, name, index=_id)

    def set_deployment_parameter(self, key, value):
        comp, _id, name = split_key(key)
        if (not _id) and is_global_ns(comp):
            self.deployment.set_deployment_parameter_global(name, value)
        else:
            self.deployment.set_deployment_parameter(comp, _id, name, value)

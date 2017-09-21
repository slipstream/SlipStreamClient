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

from slipstream.api.deployment import Deployment
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
    index = None
    if ':' in key:
        comp_id, name = key.split(':')
    else:
        return None, None, name
    if '.' in comp_id:
        comp, index = comp_id.split('.')
    else:
        comp = comp_id
    return comp, name, index


class DeploymentCommandBase(CommandBase):

    def __init__(self):
        self._dpl = None
        super(DeploymentCommandBase, self).__init__()

    def add_deployment_authn_opts_and_parse(self):
        self.parser.add_option('-d', '--deployment', dest='diid',
                               help='Deployment UUID.',
                               metavar='UUID', default='')
        self.add_endpoint_option()
        self.add_authentication_options()

        self.options, self.args = self.parser.parse_args()

        self.options.serviceurl = self.options.endpoint

    def add_component_instance_option(self):
        self.parser.add_option('--comp-instance', dest='comp_instance',
                               help='Component instance as <comp>.<id>',
                               metavar='COMP', default='')

    @property
    def deployment(self):
        if not self._dpl:
            self._dpl = Deployment(self.cimi, self._get_diid())
        return self._dpl

    def get_deployment_parameter(self, key):
        key = self._key_fqn(key)
        return self.deployment.get_deployment_parameter(*(split_key(key)))

    def set_deployment_parameter(self, key, value):
        key = self._key_fqn(key)
        self.deployment.set_deployment_parameter(*(split_key(key)), value=value)

    def _get_diid(self):
        return self.options.diid or self._get_context().get('diid')

    def _get_comp_instance(self):
        if hasattr(self.options, 'comp_instance'):
            return self.options.comp_instance or self._get_context().\
                get('node_instance_name')
        else:
            return self._get_context().get('node_instance_name')

    def _key_fqn(self, key):
        if ':' not in key:
            comp_name = self._get_comp_instance()
            if not comp_name:
                raise Exception('Enable to determine parameter name.')
            key = ':'.join([comp_name, key])
        return key

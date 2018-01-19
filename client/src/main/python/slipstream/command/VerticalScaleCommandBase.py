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

from slipstream.NodeDecorator import NodeDecorator
from slipstream.SlipStreamHttpClient import DomExtractor

from slipstream.command.CommandBase import CommandBase
from slipstream.HttpClient import HttpClient
import slipstream.util as util

etree = util.importETree()


class VerticalScaleCommandBase(CommandBase):
    """A command-line program to request vertical scaling of node instances
    in a deployment.
    """

    _usage_options = ''

    def __init__(self, argv=None):
        self.run_url = None
        self.run_dom = None
        self.node_name = None
        self.instances_to_scale = []
        self.rtp_scale_values = {}
        self._scale_state = None
        self._need_cloudservice_name = True

        self.options = None
        self.args = None

        self.endpoint = None
        super(VerticalScaleCommandBase, self).__init__(argv)

    def add_scale_options(self):
        raise NotImplementedError("add_scale_options() should be implemented.")

    def _validate_and_set_scale_options(self):
        raise NotImplementedError("_validate_and_set_scale_options() should be implemented.")

    def parse(self):
        usage = """%(prog)s %(usage_options)s
<run>        Run ID. Run should be scalable and in Ready state.
<node-name>  Node name of the instance to scale.
<ids>        IDs of the node instances to scale.""" % {'prog': '%prog',
                                                       'usage_options': self._usage_options}

        self.parser.usage = usage
        self.addEndpointOption()
        self.add_scale_options()

        self.options, self.args = self.parser.parse_args()
        self._check_args()

    def _check_args(self):
        if len(self.args) < 3:
            self.usageExitTooFewArguments()
        run_id = self.args[0]
        self.run_url = self.options.endpoint + util.RUN_RESOURCE_PATH + '/' + run_id
        self.node_name = self.args[1]

        self._validate_and_set_scale_options()

        try:
            self.instances_to_scale = map(int, self.args[2:])
        except ValueError:
            self.usageExit("Invalid ids, they must be integers")

    def doWork(self):

        client = HttpClient()
        client.verboseLevel = self.verboseLevel

        self._retrieve_and_set_run(client)

        self._check_allowed_to_scale(client)

        self._set_scale_rtps(client)

        self._set_scale_state(client)
        self._set_run_provisioning(client)

    def _set_scale_rtps(self, client):
        self.log("Requesting to scale node instances: %s" % self.instances_to_scale)

        cloudservice_name = self._get_cloudservice_name()
        cloudservice_name_with_separator = cloudservice_name and (cloudservice_name + '.') or ''

        node_url = self.run_url + "/" + self.node_name
        for _id in self.instances_to_scale:
            url = node_url + NodeDecorator.NODE_MULTIPLICITY_SEPARATOR + \
                str(_id) + NodeDecorator.NODE_PROPERTY_SEPARATOR + cloudservice_name_with_separator
            for scale_key, value in self.rtp_scale_values.items():
                client.put(url + scale_key, value)

    def _get_cloudservice_name(self):
        if self._need_cloudservice_name:
            run_params = DomExtractor.extract_run_parameters_from_run(self.run_dom)
            return run_params[self.node_name + NodeDecorator.NODE_PROPERTY_SEPARATOR +
                NodeDecorator.CLOUDSERVICE_KEY]
        else:
            return ''

    def _set_scale_state(self, client):
        node_url = self.run_url + "/" + self.node_name
        for _id in self.instances_to_scale:
            url = node_url + NodeDecorator.NODE_MULTIPLICITY_SEPARATOR + \
                str(_id) + NodeDecorator.NODE_PROPERTY_SEPARATOR + 'scale.state'
            client.put(url, self._scale_state)

    def _set_run_provisioning(self, client):
        client.put(self.run_url + '/ss:state', 'Provisioning')

    def _check_allowed_to_scale(self, client):
        err_msg = "ERROR: Run should be scalable and in Ready state."

        ss_state = self._get_ss_state(client)
        if 'Ready' != ss_state:
            self.usageExit(err_msg + " Run is in %s state." % ss_state)

        if not self._is_run_scalable():
            self.usageExit(err_msg + " Run is not scalable.")

    def _get_ss_state(self, client):
        ss_state_url = self.run_url + "/" + NodeDecorator.globalNamespacePrefix + 'state'
        _, ss_state = client.get(ss_state_url)
        return ss_state

    def _retrieve_and_set_run(self, client):
        _, run_xml = client.get(self.run_url, 'application/xml')
        self.run_dom = etree.fromstring(run_xml)

    def _is_run_scalable(self):
        scalable = DomExtractor.extract_mutable_from_run(self.run_dom)
        return util.str2bool(scalable)

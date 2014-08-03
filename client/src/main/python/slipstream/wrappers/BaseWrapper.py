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

import traceback

from slipstream.SlipStreamHttpClient import SlipStreamHttpClient
from slipstream.NodeDecorator import NodeDecorator
from slipstream.exceptions.Exceptions import NotYetSetException
from slipstream import util


class NodeInfoPublisher(SlipStreamHttpClient):
    def __init__(self, configHolder):
        super(NodeInfoPublisher, self).__init__(configHolder)

    def publish(self, nodename, vm_id, vm_ip):
        self.publish_instanceid(nodename, vm_id)
        self.publish_hostname(nodename, vm_ip)

    def publish_instanceid(self, nodename, vm_id):
        self._setRuntimeParameter(nodename, 'instanceid', vm_id)

    def publish_hostname(self, nodename, vm_ip):
        self._setRuntimeParameter(nodename, 'hostname', vm_ip)

    def publish_url_ssh(self, nodename, vm_ip, username):
        url = 'ssh://%s@%s' % (username.strip(), vm_ip.strip())
        self._setRuntimeParameter(nodename, 'url.ssh', url)

    def _setRuntimeParameter(self, nodename, key, value):
        parameter = nodename + NodeDecorator.NODE_PROPERTY_SEPARATOR + key
        self.setRuntimeParameter(parameter, value, ignoreAbort=True)


class BaseWrapper(object):

    SCALE_STATE_CREATING = 'creating'
    SCALE_STATE_CREATED = 'created'
    SCALE_STATE_OPERATIONAL = 'operational'

    SCALE_STATE_REMOVING = 'removing'
    SCALE_STATE_REMOVED = 'removed'
    SCALE_STATE_GONE = 'gone'

    def __init__(self, configHolder):
        self.ss_client = SlipStreamHttpClient(configHolder)
        self.ss_client.set_http_max_retries(self.is_mutable() and -5 or 5)
        self.ss_client.ignoreAbort = True
        self.configHolder = configHolder

        self._user_info = None
        self._run_parameters = None
        self._nodes_info = {}

    def get_slipstream_client(self):
        return self.ss_client

    def complete_state(self, node_instance_name=None):
        if not node_instance_name:
            node_instance_name = self._get_node_instance_name()
        self.ss_client.complete_state(node_instance_name)

    def reset(self):
        self.ss_client.reset()

    def fail(self, message):
        util.printError('Failing... %s' % message)
        traceback.print_exc()
        abort = self._qualifyKey(NodeDecorator.ABORT_KEY)
        self.ss_client.setRuntimeParameter(abort, message)

    def getState(self):
        key = NodeDecorator.globalNamespacePrefix + NodeDecorator.STATE_KEY
        return self.ss_client.getRuntimeParameter(key)

    def isAbort(self):
        key = NodeDecorator.globalNamespacePrefix + NodeDecorator.ABORT_KEY
        try:
            value = self.ss_client.getRuntimeParameter(key, True)
        except NotYetSetException:
            value = ''
        return (value and True) or False

    def get_run_category(self):
        return self.ss_client.get_run_category()

    def get_run_type(self):
        return self.ss_client.get_run_type()

    def _qualifyKey(self, key):
        """Qualify the key, if not already done, with the right nodename"""

        _key = key

        # Is this a reserved or special nodename?
        for reserved in NodeDecorator.reservedNodeNames:
            if _key.startswith(reserved + NodeDecorator.NODE_PROPERTY_SEPARATOR):
                return _key

        # Is the key namespaced (i.e. contains node/key separator: ':')?
        if NodeDecorator.NODE_PROPERTY_SEPARATOR in _key:
            # Is the nodename in the form: <nodename>.<index>?  If not, make it so
            # such that <nodename>:<property> -> <nodename>.1:<property
            parts = _key.split(NodeDecorator.NODE_PROPERTY_SEPARATOR)
            nodenamePart = parts[0]
            propertyPart = parts[1]  # safe since we've done the test in the if above
            parts = nodenamePart.split(NodeDecorator.NODE_MULTIPLICITY_SEPARATOR)
            nodename = parts[0]
            if len(parts) == 1:
                _key = nodename + \
                    NodeDecorator.NODE_MULTIPLICITY_SEPARATOR + \
                    NodeDecorator.nodeMultiplicityStartIndex + \
                    NodeDecorator.NODE_PROPERTY_SEPARATOR + \
                    propertyPart
            return _key

        _key = self._get_node_instance_name() + NodeDecorator.NODE_PROPERTY_SEPARATOR + _key

        return _key

    def _get_node_instance_name(self):
        return self.configHolder.nodename

    def nodename(self):
        return self._get_node_instance_name()

    def getTargets(self):
        return self.ss_client.get_node_deployment_targets()

    def get_cloud_instance_id(self):
        key = self._qualifyKey(NodeDecorator.INSTANCEID_KEY)
        return self.ss_client.getRuntimeParameter(key)

    def get_user_ssh_pubkey(self):
        userInfo = self._get_user_info('')
        return userInfo.get_public_keys()

    def need_to_stop_images(self, ignore_on_success_run_forever=False):
        # pylint: disable=unused-argument
        return False

    def is_mutable(self):
        mutable = self.ss_client.get_run_mutable()
        return util.str2bool(mutable)

    def set_scale_state_on_node_instances(self, instance_names, scale_state):
        for instance_name in instance_names:
            key = instance_name + NodeDecorator.NODE_PROPERTY_SEPARATOR + NodeDecorator.SCALE_STATE_KEY
            self.ss_client.setRuntimeParameter(key, scale_state)

    def is_scale_state_creating(self):
        return self.SCALE_STATE_CREATING == self.get_scale_state()

    def set_scale_state_operational(self):
        self.set_scale_state(self.SCALE_STATE_OPERATIONAL)

    def set_scale_state_created(self):
        self.set_scale_state(self.SCALE_STATE_CREATED)

    def set_scale_state(self, scale_state):
        '''Set scale state for this node instances.
        '''
        key = self._qualifyKey(NodeDecorator.SCALE_STATE_KEY)
        self.ss_client.setRuntimeParameter(key, scale_state)

    def get_scale_state(self):
        '''Get scale state for this node instances.
        '''
        key = self._qualifyKey(NodeDecorator.SCALE_STATE_KEY)
        return self.ss_client.getRuntimeParameter(key)

#     def _get_current_not_operational_scale_states(self):
#         '''Return {node_instance_name: scale_state, } dictionary.
#         '''
#         node_instances_not_op = {}
#         for name, instance in self.ss_client.get_nodes_instances().iteritems():

    def get_node_instances_in_scale_state(self, scale_state, cloud_service_name=None):
        instances = {}

        nodes_instances = self._get_nodes_instances(cloud_service_name)
        for instance_name, instance in nodes_instances.iteritems():
            if instance.get_scale_state() == scale_state:
                instances[instance_name] = instance

        return instances

    def send_report(self, filename):
        self.ss_client.sendReport(filename)

    #
    # Local cache of NodesInstances, Run, Run Parameters and User.
    #
    def discard_nodes_info_locally(self):
        self._nodes_info = {}

    def _get_nodes_instances(self, cloud_service_name=None):
        '''Return dict {<node-name>: {<runtime-param-name>: <value>, }, }
        '''
        if not self._nodes_info:
            self._nodes_info = self.ss_client.get_nodes_instances(cloud_service_name)
        return self._nodes_info

    def discard_run_locally(self):
        self.ss_client.discard_run()

    def discard_user_info_locally(self):
        self._user_info = None

    def _get_user_info(self, cloud_service_name):
        if self._user_info is None:
            self._user_info = self.ss_client.get_user_info(cloud_service_name)
        return self._user_info

    def discard_run_parameters_locally(self):
        self._run_parameters = None

    def _get_run_parameters(self):
        if self._run_parameters is None:
            self._run_parameters = self.ss_client.get_run_parameters()
        return self._run_parameters

    #
    # Helpers
    #
    def _terminate_run_server_side(self):
        self.ss_client.terminate_run()

    def _put_new_image_id(self, url, new_image_id):
        self.ss_client.put_new_image_id(url, new_image_id)

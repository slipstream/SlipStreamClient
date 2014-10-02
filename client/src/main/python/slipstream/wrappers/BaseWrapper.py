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

import traceback

from slipstream import util
from slipstream.SlipStreamHttpClient import SlipStreamHttpClient
from slipstream.NodeDecorator import NodeDecorator
from slipstream.exceptions.Exceptions import NotYetSetException
from slipstream.exceptions import Exceptions


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

    SCALE_STATE_DISK_RESIZING = 'disk_resizing'
    SCALE_STATE_DISK_RESIZED = 'disk_resized'

    SCALE_STATE_OPERATIONAL = 'operational'

    SCALE_STATE_REMOVING = 'removing'
    SCALE_STATE_REMOVED = 'removed'
    SCALE_STATE_GONE = 'gone'

    SCALE_STATES_TERMINAL = (SCALE_STATE_OPERATIONAL, SCALE_STATE_GONE)

    SCALE_ACTION_CREATION = 'creation'
    SCALE_ACTION_REMOVAL = 'removal'
    SCALE_ACTION_DISK_RESIZE = 'disk_resize'

    STATE_TO_ACTION = {SCALE_STATE_CREATED: SCALE_ACTION_CREATION,
                       SCALE_STATE_REMOVED: SCALE_ACTION_REMOVAL,
                       SCALE_STATE_DISK_RESIZED: SCALE_ACTION_DISK_RESIZE}

    def __init__(self, configHolder):
        self._ss_client = SlipStreamHttpClient(configHolder)
        self._ss_client.set_http_max_retries(self.is_mutable() and -5 or 5)
        self._ss_client.ignoreAbort = True
        self.configHolder = configHolder

        self._user_info = None
        self._run_parameters = None
        self._nodes_instances = {}

    def get_slipstream_client(self):
        return self._ss_client

    def complete_state(self, node_instance_name=None):
        if not node_instance_name:
            node_instance_name = self._get_node_instance_name()
        self._ss_client.complete_state(node_instance_name)

    # TODO: LS: Can we remove this method ?
    def reset(self):
        self._ss_client.reset()

    def fail(self, message):
        util.printError('Failing... %s' % message)
        traceback.print_exc()
        abort = self._qualifyKey(NodeDecorator.ABORT_KEY)
        self._ss_client.setRuntimeParameter(abort, message)

    def getState(self):
        key = NodeDecorator.globalNamespacePrefix + NodeDecorator.STATE_KEY
        return self._get_runtime_parameter(key)

    def isAbort(self):
        key = NodeDecorator.globalNamespacePrefix + NodeDecorator.ABORT_KEY
        try:
            value = self._get_runtime_parameter(key, True)
        except NotYetSetException:
            value = ''
        return (value and True) or False

    def get_run_category(self):
        return self._ss_client.get_run_category()

    def get_run_type(self):
        return self._ss_client.get_run_type()

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
        return self.configHolder.node_instance_name

    def node_instance_name(self):
        return self._get_node_instance_name()

    def getTargets(self):
        return self._ss_client.get_node_deployment_targets()

    def get_cloud_instance_id(self):
        key = self._qualifyKey(NodeDecorator.INSTANCEID_KEY)
        return self._get_runtime_parameter(key)

    def get_user_ssh_pubkey(self):
        userInfo = self._get_user_info('')
        return userInfo.get_public_keys()

    def _get_runtime_parameter(self, key, ignore_abort=False):
        return self._ss_client.getRuntimeParameter(key, ignoreAbort=ignore_abort)

    def need_to_stop_images(self, ignore_on_success_run_forever=False):
        # pylint: disable=unused-argument
        return False

    def is_mutable(self):
        mutable = self._ss_client.get_run_mutable()
        return util.str2bool(mutable)

    def set_scale_state_on_node_instances(self, instance_names, scale_state):
        for instance_name in instance_names:
            key = instance_name + NodeDecorator.NODE_PROPERTY_SEPARATOR + NodeDecorator.SCALE_STATE_KEY
            self._ss_client.setRuntimeParameter(key, scale_state)

    def is_scale_state_operational(self):
        return self.SCALE_STATE_OPERATIONAL == self.get_scale_state()

    def is_scale_state_creating(self):
        return self.SCALE_STATE_CREATING == self.get_scale_state()

    def _is_scale_state_terminal(self, state):
        return state in self.SCALE_STATES_TERMINAL

    def set_scale_state_operational(self):
        self.set_scale_state(self.SCALE_STATE_OPERATIONAL)

    def set_scale_state_created(self):
        self.set_scale_state(self.SCALE_STATE_CREATED)

    def set_scale_state(self, scale_state):
        '''Set scale state for this node instances.
        '''
        key = self._qualifyKey(NodeDecorator.SCALE_STATE_KEY)
        self._ss_client.setRuntimeParameter(key, scale_state)

    def get_scale_state(self):
        '''Get scale state for this node instances.
        '''
        key = self._qualifyKey(NodeDecorator.SCALE_STATE_KEY)
        return self._get_runtime_parameter(key)

    def _get_effective_scale_state(self, node_instance_name):
        '''Get effective node instance scale state from the server.
        '''
        key = node_instance_name + NodeDecorator.NODE_PROPERTY_SEPARATOR + \
            NodeDecorator.SCALE_STATE_KEY
        return self._get_runtime_parameter(key)

    def _get_effective_scale_states(self):
        '''Extract node instances in scaling states and update their effective
        states from the server.
        Return {scale_state: [node_instance_name, ], }
        '''
        states_instances = {}
        for node_instance_name, node_instance in self._get_nodes_instances().iteritems():
            state = node_instance.get_scale_state()
            if not self._is_scale_state_terminal(state):
                state = self._get_effective_scale_state(node_instance_name)
                states_instances.setdefault(state, []).append(node_instance_name)
        return states_instances

    def _get_global_scale_state(self):
        '''Return scale state all the node instances are in, or None.
        Raise ExecutionException if there are instances in different states.
        For consistency reasons, only single scalability action is allowed.
        '''
        states_node_instances = self._get_effective_scale_states()

        if len(states_node_instances) == 0:
            return None

        if len(states_node_instances) == 1:
            return states_node_instances.keys()[0]

        msg = "Inconsistent scaling situation. Single scaling action allowed," \
            " found: %s" % states_node_instances
        raise Exceptions.ExecutionException(msg)

    def get_global_scale_action(self):
        state = self._get_global_scale_state()
        return self._state_to_action(state)

    def get_scaling_node_and_instance_names(self):
        '''Return name of the node and the corresponding instances that are
        currently being scaled.
        Return tuple: node_name, [node_instance_name, ]
        '''
        node_names = set()
        node_instance_names = []

        for node_instance_name, node_instance in self._get_nodes_instances().iteritems():
            state = node_instance.get_scale_state()
            if not self._is_scale_state_terminal(state):
                node_names.add(node_instance.get_node_name())
                node_instance_names.append(node_instance_name)

        if len(node_names) != 1:
            msg = "Inconsistent scaling situation. Scaling of only single" \
                " node type is allowed, found: %s" % ', '.join(node_names)
            raise Exceptions.ExecutionException(msg)

        return node_names.pop(), node_instance_names

    def _state_to_action(self, state):
        return self.STATE_TO_ACTION.get(state, None)

    def get_node_instances_in_scale_state(self, scale_state, cloud_service_name=None):
        instances = {}

        nodes_instances = self._get_nodes_instances(cloud_service_name)
        for instance_name, instance in nodes_instances.iteritems():
            if instance.get_scale_state() == scale_state:
                instances[instance_name] = instance

        return instances

    def send_report(self, filename):
        self._ss_client.sendReport(filename)

    #
    # Local cache of NodesInstances, Run, Run Parameters and User.
    #
    def discard_nodes_info_locally(self):
        self._nodes_instances = {}

    def _get_nodes_instances(self, cloud_service_name=None):
        '''Return dict {<node-name>: {<runtime-param-name>: <value>, }, }
        '''
        if not self._nodes_instances:
            self._nodes_instances = self._ss_client.get_nodes_instances(cloud_service_name)
        return self._nodes_instances

    def discard_run_locally(self):
        self._ss_client.discard_run()

    def discard_user_info_locally(self):
        self._user_info = None

    def _get_user_info(self, cloud_service_name):
        if self._user_info is None:
            self._user_info = self._ss_client.get_user_info(cloud_service_name)
        return self._user_info

    def discard_run_parameters_locally(self):
        self._run_parameters = None

    def _get_run_parameters(self):
        if self._run_parameters is None:
            self._run_parameters = self._ss_client.get_run_parameters()
        return self._run_parameters

    #
    # Helpers
    #
    def _terminate_run_server_side(self):
        self._ss_client.terminate_run()

    def _put_new_image_id(self, url, new_image_id):
        self._ss_client.put_new_image_id(url, new_image_id)

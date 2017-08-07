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
import os
import time

import traceback

from slipstream import util
from slipstream.SlipStreamHttpClient import SlipStreamHttpClient
from slipstream.NodeDecorator import NodeDecorator
from slipstream.exceptions import Exceptions
from slipstream.Client import Client
from slipstream.NodeInstance import NodeInstance
from slipstream.exceptions.Exceptions import TimeoutException, \
    ExecutionException, InconsistentScaleStateError, InconsistentScalingNodesError


class RuntimeParameter(object):

    def __init__(self, config_holder):
        self._ss = SlipStreamHttpClient(config_holder)
        self._ss.set_retry(True)

    def set(self, parameter, value, ignore_abort=True):
        self._ss.setRuntimeParameter(parameter, value, ignoreAbort=ignore_abort)

    def set_from_parts(self, category, key, value, ignore_abort=True):
        parameter = category + NodeDecorator.NODE_PROPERTY_SEPARATOR + key
        self.set(parameter, value, ignore_abort)


class NodeInfoPublisher(SlipStreamHttpClient):
    def __init__(self, config_holder):
        super(NodeInfoPublisher, self).__init__(config_holder)
        self.set_retry(True)

    def publish(self, nodename, vm_id, vm_ip):
        self.publish_instanceid(nodename, vm_id)
        self.publish_hostname(nodename, vm_ip)

    def publish_instanceid(self, nodename, vm_id):
        self._set_runtime_parameter(nodename, 'instanceid', vm_id)

    def publish_hostname(self, nodename, vm_ip):
        self._set_runtime_parameter(nodename, 'hostname', vm_ip)

    def publish_url_ssh(self, nodename, vm_ip, username):
        url = 'ssh://%s@%s' % (username.strip(), vm_ip.strip())
        self._set_runtime_parameter(nodename, 'url.ssh', url)

    def _set_runtime_parameter(self, nodename, key, value):
        parameter = nodename + NodeDecorator.NODE_PROPERTY_SEPARATOR + key
        self.setRuntimeParameter(parameter, value, ignoreAbort=True)


SS_POLLING_INTERVAL_SEC = 10


class BaseWrapper(object):

    SCALE_ACTION_CREATION = 'vm_create'
    SCALE_STATE_CREATING = 'creating'
    SCALE_STATE_CREATED = 'created'

    SCALE_ACTION_REMOVAL = 'vm_remove'
    SCALE_STATE_REMOVING = 'removing'
    SCALE_STATE_REMOVED = 'removed'
    SCALE_STATE_GONE = 'gone'

    SCALE_ACTION_RESIZE = 'vm_resize'
    SCALE_STATE_RESIZING = 'resizing'
    SCALE_STATE_RESIZED = 'resized'

    SCALE_ACTION_DISK_ATTACH = 'disk_attach'
    SCALE_STATE_DISK_ATTACHING = 'disk_attaching'
    SCALE_STATE_DISK_ATTACHED = 'disk_attached'

    SCALE_ACTION_DISK_DETACH = 'disk_detach'
    SCALE_STATE_DISK_DETACHING = 'disk_detaching'
    SCALE_STATE_DISK_DETACHED = 'disk_detached'

    SCALE_STATES_START_STOP_MAP = {
        SCALE_STATE_CREATING: SCALE_STATE_CREATED,
        SCALE_STATE_REMOVING: SCALE_STATE_REMOVED,
        SCALE_STATE_RESIZING: SCALE_STATE_RESIZED,
        SCALE_STATE_DISK_ATTACHING: SCALE_STATE_DISK_ATTACHED,
        SCALE_STATE_DISK_DETACHING: SCALE_STATE_DISK_DETACHED}

    SCALE_STATE_OPERATIONAL = 'operational'

    SCALE_STATES_TERMINAL = (SCALE_STATE_OPERATIONAL, SCALE_STATE_GONE)

    SCALE_STATES_VERTICAL_SCALABILITY = (SCALE_STATE_RESIZING,
                                         SCALE_STATE_DISK_ATTACHING,
                                         SCALE_STATE_DISK_DETACHING)

    STATE_TO_ACTION = {
        SCALE_STATE_CREATING: SCALE_ACTION_CREATION,
        SCALE_STATE_CREATED: SCALE_ACTION_CREATION,

        SCALE_STATE_REMOVING: SCALE_ACTION_REMOVAL,
        SCALE_STATE_REMOVED: SCALE_ACTION_REMOVAL,

        SCALE_STATE_RESIZING: SCALE_ACTION_RESIZE,
        SCALE_STATE_RESIZED: SCALE_ACTION_RESIZE,

        SCALE_STATE_DISK_ATTACHING: SCALE_ACTION_DISK_ATTACH,
        SCALE_STATE_DISK_ATTACHED: SCALE_ACTION_DISK_ATTACH,

        SCALE_STATE_DISK_DETACHING: SCALE_ACTION_DISK_DETACH,
        SCALE_STATE_DISK_DETACHED: SCALE_ACTION_DISK_DETACH,
        }

    def __init__(self, config_holder):
        self._ss_client = SlipStreamHttpClient(config_holder)
        self._ss_client.set_retry(True)
        self._ss_client.ignoreAbort = True

        self.my_node_instance_name = self._get_my_node_instance_name(config_holder)

        self._config_holder = config_holder

        self._user_info = None
        self._run_parameters = None
        self._nodes_instances = {}

        self._state_start_time = None

    @staticmethod
    def _get_my_node_instance_name(config_holder):
        try:
            return config_holder.node_instance_name
        except Exception:
            raise Exceptions.ExecutionException('Failed to get the node instance name of the the current VM')

    def get_my_node_instance_name(self):
        return self.my_node_instance_name

    def get_slipstream_client(self):
        return self._ss_client

    def complete_state(self, node_instance_name=None):
        if not node_instance_name:
            node_instance_name = self.get_my_node_instance_name()
        self._ss_client.complete_state(node_instance_name)

    def fail(self, message):
        key = self._qualifyKey(NodeDecorator.ABORT_KEY)
        self._fail(key, message)

    def fail_global(self, message):
        key = NodeDecorator.globalNamespacePrefix + NodeDecorator.ABORT_KEY
        self._fail(key, message)

    def _fail(self, key, message):
        util.printError('Failing... %s' % message)
        traceback.print_exc()
        value = util.truncate_middle(Client.VALUE_LENGTH_LIMIT, message, '\n(truncated)\n')
        self._ss_client.setRuntimeParameter(key, value)

    def getState(self):
        key = NodeDecorator.globalNamespacePrefix + NodeDecorator.STATE_KEY
        return self._get_runtime_parameter(key)

    def get_recovery_mode(self):
        key = NodeDecorator.globalNamespacePrefix + NodeDecorator.RECOVERY_MODE_KEY
        return util.str2bool(self._get_runtime_parameter(key))

    def isAbort(self):
        key = NodeDecorator.globalNamespacePrefix + NodeDecorator.ABORT_KEY
        try:
            value = self._get_runtime_parameter(key, True)
        except Exceptions.NotYetSetException:
            value = ''
        return (value and True) or False

    def get_max_iaas_workers(self):
        """Available only on orchestrator.
        """
        return self._get_runtime_parameter(self._qualifyKey("max.iaas.workers"))

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

        _key = self.get_my_node_instance_name() + NodeDecorator.NODE_PROPERTY_SEPARATOR + _key

        return _key

    def get_cloud_instance_id(self):
        key = self._qualifyKey(NodeDecorator.INSTANCEID_KEY)
        return self._get_runtime_parameter(key)

    def get_user_ssh_pubkey(self):
        userInfo = self._get_user_info('')
        return userInfo.get_public_keys()

    def get_pre_scale_done(self, node_instance_or_name=None):
        """Get pre.scale.done RTP for the current node instance or for the requested one
        (by NodeInstance object or node instance name).
        :param node_instance_or_name: node instance or node instance name
        :type node_instance_or_name: NodeInstance or str
        :return:
        """
        if node_instance_or_name:
            key = self._build_rtp(node_instance_or_name, NodeDecorator.PRE_SCALE_DONE)
        else:
            key = self._qualifyKey(NodeDecorator.PRE_SCALE_DONE)
        return self._get_runtime_parameter(key)

    def is_pre_scale_done(self, node_instance_or_name=None):
        """Checks if pre-scale action is done on itself (node_instance_or_name is not provided)
        or on a requested node instance (by NodeInstance object or node instance name).
        :param node_instance_or_name: node instance or node instance name
        :type node_instance_or_name: NodeInstance or str
        :return: True or False
        :rtype: ``bool``
        """
        value = self.get_pre_scale_done(node_instance_or_name)
        return NodeDecorator.PRE_SCALE_DONE_SUCCESS == value

    @staticmethod
    def _build_rtp(category, key):
        if isinstance(category, NodeInstance):
            category = category.get_name()
        return category + NodeDecorator.NODE_PROPERTY_SEPARATOR + key

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
        """Set scale state for this node instances.
        """
        key = self._qualifyKey(NodeDecorator.SCALE_STATE_KEY)
        self._ss_client.setRuntimeParameter(key, scale_state)

    def get_scale_state(self):
        """Get scale state for this node instances.
        """
        key = self._qualifyKey(NodeDecorator.SCALE_STATE_KEY)
        return self._get_runtime_parameter(key)

    def _get_effective_scale_state(self, node_instance_or_name):
        """Get effective node instance scale state from the server.
        """
        if isinstance(node_instance_or_name, NodeInstance):
            node_instance_or_name = node_instance_or_name.get_name()
        key = node_instance_or_name + NodeDecorator.NODE_PROPERTY_SEPARATOR + \
            NodeDecorator.SCALE_STATE_KEY
        return self._get_runtime_parameter(key)

    def _get_effective_scale_states(self):
        """Extract node instances in scaling states and update their effective
        states from the server.
        Return {scale_state: [node_instance_name, ], }
        """
        states_instances = {}
        for node_instance_name, node_instance in self._get_nodes_instances().iteritems():
            state = node_instance.get_scale_state()
            if not self._is_scale_state_terminal(state):
                state = self._get_effective_scale_state(node_instance_name)
                states_instances.setdefault(state, []).append(node_instance_name)
        return states_instances

    def _get_global_scale_state(self):
        """Return scale state all the node instances are in, or None.
        Raise InconsistentScaleStateError if there are instances in different states.
        For consistency reasons, only single scalability action is allowed.
        """
        states_node_instances = self._get_effective_scale_states()

        if len(states_node_instances) == 0:
            return None

        if len(states_node_instances) == 1:
            return states_node_instances.keys()[0]

        msg = "Inconsistent scaling situation. Single scaling action allowed," \
            " found: %s" % states_node_instances
        raise InconsistentScaleStateError(msg)

    def get_global_scale_action(self):
        state = self._get_global_scale_state()
        return self._state_to_action(state)

    def get_scale_action(self):
        state = self.get_scale_state()
        return self._state_to_action(state)

    def check_scale_state_consistency(self):
        states_node_instances = self._get_effective_scale_states()
        states_node_instances.pop(self.SCALE_STATE_REMOVED, None)

        if len(states_node_instances) > 1:
            msg = "Inconsistent scaling situation. Single scaling action allowed," \
                  " found: %s" % states_node_instances
            raise InconsistentScaleStateError(msg)

    def get_scaling_node_and_instance_names(self):
        """Return name of the node and the corresponding instances that are
        currently being scaled.
        :return: two-tuple with scaling node name and a list of node instance names.
        :rtype: (node_name, [node_instance_name, ])
        :raises: ExecutionExcetion if more than one node type is being scaled.
        """
        node_names = set()
        node_instance_names = []

        for node_instance_name, node_instance in self._get_nodes_instances().iteritems():
            state = node_instance.get_scale_state()
            if not self._is_scale_state_terminal(state):
                node_names.add(node_instance.get_node_name())
                node_instance_names.append(node_instance_name)

        if len(node_names) > 1:
            msg = "Inconsistent scaling situation. Scaling of only single" \
                " node type is allowed, found: %s" % ', '.join(node_names)
            raise InconsistentScalingNodesError(msg)

        if not node_names:
            return '', node_instance_names
        else:
            return node_names.pop(), node_instance_names

    def _state_to_action(self, state):
        return self.STATE_TO_ACTION.get(state, None)

    def get_node_instances_in_scale_state(self, scale_state):
        """Return dict {<node_instance_name>: NodeInstance, } with the node instances
        in the scale_state.
        """
        instances = {}

        nodes_instances = self._get_nodes_instances()
        for instance_name, instance in nodes_instances.iteritems():
            if instance.get_scale_state() == scale_state:
                instances[instance_name] = instance

        return instances

    def send_report(self, filename):
        self._ss_client.sendReport(filename)

    def set_statecustom(self, message):
        key = self._qualifyKey(NodeDecorator.STATECUSTOM_KEY)
        self._ss_client.setRuntimeParameter(key, message)

    def set_pre_scale_done(self):
        """To be called by NodeDeploymentExecutor.  Not thread-safe.
        """
        key = self._qualifyKey(NodeDecorator.PRE_SCALE_DONE)
        self._ss_client.setRuntimeParameter(key, NodeDecorator.PRE_SCALE_DONE_SUCCESS)

    def unset_pre_scale_done(self):
        """To be called by NodeDeploymentExecutor.  Not thread-safe.
        """
        key = self._qualifyKey(NodeDecorator.PRE_SCALE_DONE)
        self._ss_client.setRuntimeParameter(key, 'false')

    def set_scale_action_done(self):
        """To be called by NodeDeploymentExecutor. Sets an end of the scaling action.
        Not thread-safe.
        """
        scale_state_start = self.get_scale_state()
        key = self._qualifyKey(NodeDecorator.SCALE_STATE_KEY)
        try:
            scale_done = self.SCALE_STATES_START_STOP_MAP[scale_state_start]
        except KeyError:
            raise ExecutionException(
                "Unable to set the end of scale action on %s. Don't know start->done mapping for %s." %
                (key, scale_state_start))
        else:
            self._ss_client.setRuntimeParameter(key, scale_done)

    def set_scale_iaas_done(self, node_instance_or_name):
        """To be called on Orchestrator.  Thread-safe implementation.
        :param node_instance_or_name: node instance object or node instance name
        :type node_instance_or_name: NodeInstance or str
        """
        self._set_scale_iaas_done_rtp(node_instance_or_name, NodeDecorator.SCALE_IAAS_DONE_SUCCESS)

    def set_scale_iaas_done_and_set_attached_disk(self, node_instance_or_name, disk):
        """To be called on Orchestrator.  Thread-safe implementation.
        :param node_instance_or_name: node instance object or node instance name
        :type node_instance_or_name: NodeInstance or str
        :param disk: identifier of the attached disk
        :type disk: str
        """
        self.set_scale_iaas_done(node_instance_or_name)
        self.set_attached_disk(node_instance_or_name, disk)

    def unset_scale_iaas_done(self, node_instance_or_name):
        """To be called on Orchestrator.  Thread-safe implementation.
        :param node_instance_or_name: node instance object or node instance name
        :type node_instance_or_name: NodeInstance or str
        """
        self._set_scale_iaas_done_rtp(node_instance_or_name, 'false')

    def _set_scale_iaas_done_rtp(self, node_instance_or_name, value):
        """To be called on Orchestrator.  Thread-safe implementation.
        :param node_instance_or_name: node instance object or node instance name
        :type node_instance_or_name: NodeInstance or str
        """
        self._set_rtp(node_instance_or_name, NodeDecorator.SCALE_IAAS_DONE, value)

    def set_attached_disk(self, node_instance_or_name, disk):
        self._set_attached_disk_rtp(node_instance_or_name, disk)

    def _set_attached_disk_rtp(self, node_instance_or_name, value):
        self._set_rtp(node_instance_or_name, NodeDecorator.SCALE_DISK_ATTACHED_DEVICE, value)

    def _set_rtp(self, node_instance_or_name, key, value):
        if isinstance(node_instance_or_name, NodeInstance):
            node_instance_or_name = node_instance_or_name.get_name()
        rtp = node_instance_or_name + NodeDecorator.NODE_PROPERTY_SEPARATOR + key
        self._set_runtime_parameter(rtp, value)

    def is_vertical_scaling(self):
        return self._get_global_scale_state() in self.SCALE_STATES_VERTICAL_SCALABILITY

    def is_vertical_scaling_vm(self):
        return self.get_scale_state() in self.SCALE_STATES_VERTICAL_SCALABILITY

    def is_horizontal_scale_down(self):
        return self._get_global_scale_state() == self.SCALE_STATE_REMOVING

    def is_horizontal_scale_down_vm(self):
        return self.get_scale_state() == self.SCALE_STATE_REMOVING

    def _set_runtime_parameter(self, parameter, value):
        # Needed for thread safety.
        RuntimeParameter(self._get_config_holder_deepcopy()).set(parameter, value)

    def _get_config_holder(self):
        return self._config_holder

    def _get_config_holder_deepcopy(self):
        return self._get_config_holder().deepcopy()

    @staticmethod
    def _wait_rtp_equals(node_instances, expected_value, rtp_getter, timeout_at,
                         polling_interval=None):
        """Blocking wait with timeout until the RTP is set to the expected value
        on the set of node instances.
        NB! RTP name is NOT known. A getter function is used to get the value.

        :param node_instances: list of node instances
        :type node_instances: list [NodeInstance, ]
        :param expected_value: value to which the rtp should be set to
        :type expected_value: str
        :param rtp_getter: function to get the rtp; should accept NodeInstance or node instance name
        :type rtp_getter: callable
        :param timeout_at: wall-clock time to timeout at
        :type timeout_at: int or float
        """
        node_instance_to_result = dict([(ni.get_name(), False) for ni in node_instances])
        polling_interval = polling_interval or SS_POLLING_INTERVAL_SEC
        _polling_interval = 0
        while not all(node_instance_to_result.values()):
            if (timeout_at > 0) and (time.time() >= timeout_at):
                raise TimeoutException("Timed out while waiting for RTP to be set to '%s' on %s." %
                                       (expected_value, node_instance_to_result))
            time.sleep(_polling_interval)
            for node_instance in node_instances:
                node_instance_name = node_instance.get_name()
                if not node_instance_to_result[node_instance_name]:
                    if expected_value == rtp_getter(node_instance):
                        node_instance_to_result[node_instance_name] = expected_value
            _polling_interval = polling_interval

    def wait_scale_iaas_done(self):
        """To be called by NodeDeployentExecutor on the node instance.
        Blocking wait (with timeout) until RTP scale.iaas.done is set by Orchestrator.
        :raises: TimeoutException
        """
        timeout_at = 0 # no timeout
        self._log('Waiting for Orchestrator to finish scaling this node instance (no timeout).')

        node_instances = [self.get_my_node_instance()]

        self._wait_rtp_equals(node_instances, NodeDecorator.SCALE_IAAS_DONE_SUCCESS,
                              self.get_scale_iaas_done, timeout_at)

        self._log('All node instances finished pre-scaling.')

    def get_scale_iaas_done(self, node_instance_or_name):
        parameter = self._build_rtp(node_instance_or_name, NodeDecorator.SCALE_IAAS_DONE)
        return self._get_runtime_parameter(parameter)

    def _get_cloud_service_name(self):
        return os.environ[util.ENV_CONNECTOR_INSTANCE]

    def set_state_start_time(self):
        self._state_start_time = time.time()

    def get_state_start_time(self):
        return (self._state_start_time is None) and time.time() or self._state_start_time

    #
    # Local cache of NodesInstances, Run, Run Parameters and User.
    #
    def discard_nodes_info_locally(self):
        self._nodes_instances = {}

    def _get_nodes_instances(self):
        """Return dict {<node_instance_name>: NodeInstance, }
        """
        node_instances = self._get_nodes_instances_with_orchestrators()
        return dict([(k, ni) for k, ni in node_instances.iteritems() if not ni.is_orchestrator()])

    def _get_nodes_instances_with_orchestrators(self):
        """Return dict {<node_instance_name>: NodeInstance, }
        """
        if not self._nodes_instances:
            self._nodes_instances = self._ss_client.get_nodes_instances(self._get_cloud_service_name())
        return self._nodes_instances

    def get_my_node_instance(self):
        node_name = self.get_my_node_instance_name()
        return self._get_nodes_instances_with_orchestrators().get(node_name)

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

    def has_to_execute_build_recipes(self):
        run_parameters = self._get_run_parameters()

        key = self.get_my_node_instance_name().rsplit(NodeDecorator.NODE_MULTIPLICITY_SEPARATOR, 1)[0] \
              + NodeDecorator.NODE_PROPERTY_SEPARATOR \
              + NodeDecorator.RUN_BUILD_RECIPES_KEY

        return util.str2bool(run_parameters.get(key))

    def clean_local_cache(self):
        self.discard_run_locally()
        self.discard_nodes_info_locally()
        self.discard_run_parameters_locally()

    #
    # Helpers
    #
    def _terminate_run_server_side(self):
        self._ss_client.terminate_run()

    def _put_new_image_id(self, url, new_image_id):
        self._ss_client.put_new_image_id(url, new_image_id)

    def _log_and_set_statecustom(self, msg):
        self._log(msg)
        try:
            self.set_statecustom(msg)
        except Exception as ex:
            self._log('Failed to set statecustom with: %s' % str(ex))

    @staticmethod
    def _log(msg):
        util.printDetail(msg, verboseThreshold=0)


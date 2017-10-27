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

import time

from slipstream.wrappers.BaseWrapper import BaseWrapper
from slipstream.cloudconnectors.CloudConnectorFactory import CloudConnectorFactory
from slipstream import util
from slipstream.NodeDecorator import NodeDecorator
from slipstream.exceptions.Exceptions import ExecutionException


class CloudWrapper(BaseWrapper):

    WAIT_INSTANCES_PROVISIONED_MIN = 30
    WAIT_TIME_PERCENTAGE = .8

    KEEP_RUNNING_NEVER = 'never'
    KEEP_RUNNING_ALWAYS = 'always'
    KEEP_RUNNING_ON_ERROR = 'on-error'
    KEEP_RUNNING_ON_SUCCESS = 'on-success'

    KEEP_RUNNING_DEFAULT = KEEP_RUNNING_ON_SUCCESS

    KEEP_RUNNING_VALUES = [KEEP_RUNNING_NEVER,
                           KEEP_RUNNING_ALWAYS,
                           KEEP_RUNNING_ON_ERROR,
                           KEEP_RUNNING_ON_SUCCESS]

    def __init__(self, config_holder):
        super(CloudWrapper, self).__init__(config_holder)

        self._instance_names_to_be_gone = []

        # Explicitly call initCloudConnector() to set the cloud connector.
        self._cloud_client = None
        self.imagesStopped = False

        self._instance_names_force_to_compete_states = []

    def initCloudConnector(self, config_holder=None):
        self._cloud_client = CloudConnectorFactory.createConnector(
            config_holder or self._get_config_holder())
        self._cloud_client.set_slipstream_client_as_listener(self.get_slipstream_client())

    def set_max_iaas_workers(self):
        self._cloud_client.max_iaas_workers = self.get_max_iaas_workers()

    def build_image(self):
        user_info = self._get_user_info(self._get_cloud_service_name())

        node_instance = self._get_node_instances_to_start().get(NodeDecorator.MACHINE_NAME)
        if node_instance is None:
            raise ExecutionException('Failed to get node instance for instance named "%s"' %
                                     NodeDecorator.MACHINE_NAME)

        new_id = self._cloud_client.build_image(user_info, node_instance)

        self._update_slipstream_image(node_instance, new_id)

    def start_node_instances(self):
        nodes_instances = self._get_node_instances_to_start()
        if not nodes_instances:
            self._log_and_set_statecustom('No node instances to start [%s].' %
                                          util.toTimeInIso8601(time.time()))
            return

        self._start_nodes_and_clients(
            self._get_user_info(self._get_cloud_service_name()), nodes_instances)

        self.clean_local_cache()

        nodes_instances_list = self._get_node_instances_to_follow(nodes_instances.keys())
        self._check_provisioning(nodes_instances_list)

    def _get_node_instances_to_follow(self, ni_names_starting):
        """
        ni_names_to_be_started : list of node instance names [string, ]
        """
        all_node_instances = self._get_nodes_instances()
        instances = []
        for name, instance in all_node_instances.iteritems():
            if name in ni_names_starting:
                instances.append(instance)
        return instances

    def _start_nodes_and_clients(self, user_info, nodes_instances):
        time_start_iaas_provision = time.time()
        self._log_and_set_statecustom('Requesting provisioning of node instances [%s].' %
                                      util.toTimeInIso8601(time_start_iaas_provision))
        self._cloud_client.start_nodes_and_clients(user_info, nodes_instances)
        self._log_and_set_statecustom('Provisioning of node instances requested [%s]. Time took to provision %s.' %
                                      (util.toTimeInIso8601(time.time()),
                                       util.seconds_to_hms_str(time.time() - time_start_iaas_provision)))

    def _get_state_timeout_time(self):
        """Return wall-clock time until which the provisioning is allowed to take place.
        80% of the user's General.Timeout value is used.
        """
        user_timeout_min = self._get_user_timeout()
        # Wait less than defined by user.
        timeout_min = int(user_timeout_min * self.WAIT_TIME_PERCENTAGE)
        return self.get_state_start_time() + timeout_min * 60

    def _get_user_timeout(self):
        """
        :return: timeout in minutes
        :rtype: int
        """
        user_info = self._get_user_info(self._get_cloud_service_name())
        return int(user_info.get_general('Timeout', self.WAIT_INSTANCES_PROVISIONED_MIN))

    def _check_provisioning(self, node_instances):
        """
        node_instances list [NodeInstance, ]
        """
        allowed_failed_vms_per_node = self._get_allowed_provisioning_failures_per_node(node_instances)

        if self._need_to_wait_instances_provisioned(allowed_failed_vms_per_node):
            all_provisioned = self._sleep_while_instances_provisioned(
                self._get_state_timeout_time(), node_instances, allowed_failed_vms_per_node)
            if self.isAbort():
                return
            if not all_provisioned:
                self._check_instances_provisioned(node_instances, allowed_failed_vms_per_node)
            else:
                self._log_and_set_statecustom('All instances were provisioned. Moving on.')

    def _need_to_wait_instances_provisioned(self, allowed_failed_vms_per_node):
        """
        allowed_failed_vms_per_node dict : {'node_name': integer, }
        """
        return max(allowed_failed_vms_per_node.values()) > 0

    def _sleep_while_instances_provisioned(self, provisioning_stop_time, node_instances, allowed_failed_vms_per_node):
        """
        provisioning_stop_time (wall-clock time until the monitoring loop should run) : int
        node_instances list [NodeInstance, ]
        allowed_failed_vms_per_node dict : {'node_name': integer, }

        Return True if all it was detected that all instances were provisioned,
        False otherwise.

        """
        n_to_provision = len(node_instances)
        self._log('Waiting until %s for %s instances to be provisioned.' %
                  (util.toTimeInIso8601(provisioning_stop_time), n_to_provision))
        self._log('Allowed number of failed instances per node: %s' %
                  allowed_failed_vms_per_node)
        all_provisioned = False
        i = 1
        n_failed_on_iaas = 0
        n_failed_on_iaas_timestamp = 'not checked'
        while time.time() < provisioning_stop_time:
            time.sleep(30)
            if self.isAbort():
                self._log_and_set_statecustom('Abort flag detected. Stop waiting for '
                                              'instances to be provisioned.')
                break
            n_creating = self._get_in_creating_number()
            n_creating_timestamp = util.toTimeInIso8601(time.time())
            if n_creating == 0:
                all_provisioned = True
                self._log_and_set_statecustom('All instances provisioned. Exiting waiting loop.')
                break
            if i % 4 == 0:
                instances_failed_iaas = self._get_failed_instances_on_iaas(node_instances)
                n_failed_on_iaas_timestamp = util.toTimeInIso8601(time.time())
                if instances_failed_iaas:
                    self._check_too_many_failures(allowed_failed_vms_per_node,
                                                  instances_failed_iaas, 'IaaS')
                    n_failed_on_iaas = len(util.flatten_list_of_lists(instances_failed_iaas.values()))
                    if n_failed_on_iaas == n_creating:
                        self._log('Number of failed on IaaS (%s) == in "creating" (%s).  Existing waiting loop.' %
                                  (n_failed_on_iaas, n_creating))
                        break
            i += 1

            timeout_after = util.seconds_to_hms_str(provisioning_stop_time - time.time())
            self._log_and_set_statecustom('Stats: to provision %s, in "creating" %s [%s], failed on IaaS %s [%s], timeout after %s.' %
                                          (n_to_provision, n_creating, n_creating_timestamp, n_failed_on_iaas,
                                           n_failed_on_iaas_timestamp, timeout_after))
        return all_provisioned

    def _get_in_creating_number(self):
        self.clean_local_cache()
        creating_per_node = self._get_creating_node_instances()
        return len(util.flatten_list_of_lists(creating_per_node.values()))

    def _check_too_many_failures(self, allowed_failed_vms_per_node, instances_failed, context):
        """
        allowed_failed_vms_per_node dict : {'node_name': integer, }
        instances_failed dict : {'node_name': [NodeInstance, ], }
        context : string
        """
        if any(instances_failed.values()):
            self._log_and_set_statecustom("WARNING: Instances failed (%s): %s" %
                (context, self._get_node_instance_names_from_nodes_dict(instances_failed)))
            for node_name, allowed_failed in allowed_failed_vms_per_node.iteritems():
                failed = len(instances_failed.get(node_name, []))
                if failed > allowed_failed:
                    raise ExecutionException(
                        "Number of failed instances (%s) %s is higher than requested tolerable %s for node '%s'" %
                        (context, failed, allowed_failed, node_name))

    def _check_instances_provisioned(self, node_instances, allowed_failed_vms_per_node):
        """
        node_instances list : [NodeInstance, ]
        allowed_failed_vms_per_node dict : {'node_name': integer, }
        """

        # Node instances failed on IaaS level.
        self._check_too_many_failures(allowed_failed_vms_per_node,
                                      self._get_failed_instances_on_iaas(node_instances),
                                      'IaaS')

        # Force re-fetching Run from server.
        self.clean_local_cache()

        # Node instances didn't come back to SlipStream.
        instances_still_creating = self._get_creating_node_instances()
        self._check_too_many_failures(allowed_failed_vms_per_node, instances_still_creating, 'creating')

        # Set server side for the VMs to be terminated.
        instance_names_to_remove = self._get_node_instance_names_from_nodes_dict(instances_still_creating)
        self._log_and_set_statecustom('Instances to be removed: %s' % instance_names_to_remove)
        self.set_scale_state_on_node_instances(instance_names_to_remove, self.SCALE_STATE_REMOVING)
        self.delete_instances_from_run_server_side(instances_still_creating)

        self.clean_local_cache()

        # Register instances for forceful state completion.
        self._instance_names_force_to_compete_states = instance_names_to_remove

    def _get_allowed_provisioning_failures_per_node(self, node_instances):
        """Return {'node_name': integer, }
        Input: node_instances list [NodeInstance, ]
        """
        max_failures_per_node = {}
        for ni in node_instances:
            if ni.get_node_name() not in max_failures_per_node:
                try:
                    max_failures = int(ni.get_max_provisioning_failures())
                except ValueError:
                    raise ExecutionException("Failed to convert 'max provisioning "
                                             "failures' to int for node %s." % ni.get_node_name())
                max_failures_per_node[ni.get_node_name()] = max_failures
        return max_failures_per_node

    def _get_failed_instances_on_iaas(self, node_instances):
        """Return dict {'node_name': [NodeInstance, ], } of failed on IaaS level
        node instances.
        Input: node_instances list [NodeInstance, ]
        """
        vm_id_to_instance = {}
        for instance in node_instances:
            vm_id_to_instance[instance.get_instance_id()] = instance
        vm_ids = vm_id_to_instance.keys()
        vms = self._cloud_client.list_instances()
        failed_instances = {}
        for vm in vms:
            vm_id = self._cloud_client._vm_get_id_from_list_instances(vm)
            if (vm_id in vm_ids) and self._cloud_client._has_vm_failed(vm):
                instance = vm_id_to_instance[vm_id]
                failed_instances.setdefault(instance.get_node_name(), []).append(instance)
        return failed_instances

    def _get_creating_node_instances(self):
        """Return dict {'node_name': [NodeInstance, ], } of instances that
        hasn't reported back to SlipStream server.
        """
        instances = self.get_node_instances_in_scale_state(self.SCALE_STATE_CREATING)
        creating_instances = {}
        for instance in instances.values():
            creating_instances.setdefault(instance.get_node_name(), []).append(instance)
        return creating_instances

    def _get_node_instances_to_start(self):
        return self.get_node_instances_in_scale_state(self.SCALE_STATE_CREATING)

    def _get_node_instances_to_stop(self):
        return self.get_node_instances_in_scale_state(self.SCALE_STATE_REMOVING)

    def stop_node_instances(self):
        """
        TODO: wait pre.scale.done == True if it's not FT case. (How to discover FT context?)
        """
        node_instances_to_stop = self._get_node_instances_to_stop()
        if not node_instances_to_stop:
            self._log_and_set_statecustom('No node instances to stop [%s].' %
                                          util.toTimeInIso8601(time.time()))
            return
        instance_names = ','.join(
            self._get_node_instance_names_from_nodeinstances_dict(node_instances_to_stop))
        self._log_and_set_statecustom('Node instances to stop: %s [%s].' %
                                      (instance_names, util.toTimeInIso8601(time.time())))
        # TODO: wait pre.scale.done == True if it's not FT case. (How to discover FT context?)
        self._cloud_client.stop_node_instances(node_instances_to_stop.values())

        instance_names_removed = node_instances_to_stop.keys()
        self.set_scale_state_on_node_instances(instance_names_removed,
                                               self.SCALE_STATE_REMOVED)

        # Cache instance names that are to be set as 'gone' at Ready state.
        self._instance_names_to_be_gone = instance_names_removed

    def set_removed_instances_as_gone(self):
        '''Using cached list of instance names that were set as 'removed'.
        '''
        self.set_scale_state_on_node_instances(self._instance_names_to_be_gone,
                                               self.SCALE_STATE_GONE)
        self._instance_names_to_be_gone = {}

    def stopCreator(self):
        if self.need_to_stop_images(True):
            creator_id = self._cloud_client.get_creator_vm_id()
            if creator_id:
                if not self._is_vapp():
                    self._cloud_client.stop_vms_by_ids([creator_id])
                elif not self._is_build_in_single_vapp():
                    self._cloud_client.stop_vapps_by_ids([creator_id])

    def stopNodes(self):
        if self.need_to_stop_images():
            if not self._is_vapp():
                self._cloud_client.stop_deployment()
            self.imagesStopped = True

    def stopOrchestrator(self, is_build_image=False):
        if is_build_image:
            self.stopOrchestratorBuild()
        else:
            self.stopOrchestratorDeployment()

    def stopOrchestratorBuild(self):
        if self.need_to_stop_images(True):
            orch_id = self.get_cloud_instance_id()

            if self._is_vapp():
                if self._orchestrator_can_kill_itself_or_its_vapp():
                    if self._is_build_in_single_vapp():
                        self._cloud_client.stop_deployment()
                    else:
                        self._cloud_client.stop_vapps_by_ids([orch_id])
                else:
                    self._terminate_run_server_side()
            else:
                if self._orchestrator_can_kill_itself_or_its_vapp():
                    self._cloud_client.stop_vms_by_ids([orch_id])
                else:
                    self._terminate_run_server_side()

    def stopOrchestratorDeployment(self):
        if self._is_vapp() and self.need_to_stop_images():
            if self._orchestrator_can_kill_itself_or_its_vapp():
                self._cloud_client.stop_deployment()
            else:
                self._terminate_run_server_side()
        elif self.need_to_stop_images() and not self._orchestrator_can_kill_itself_or_its_vapp():
            self._terminate_run_server_side()
        else:
            orch_id = self.get_cloud_instance_id()
            self._cloud_client.stop_vms_by_ids([orch_id])

    def _is_build_in_single_vapp(self):
        return self._cloud_client.has_capability(
            self._cloud_client.CAPABILITY_BUILD_IN_SINGLE_VAPP)

    def _is_vapp(self):
        return self._cloud_client.has_capability(self._cloud_client.CAPABILITY_VAPP)

    def _orchestrator_can_kill_itself_or_its_vapp(self):
        return self._cloud_client.has_capability(
            self._cloud_client.CAPABILITY_ORCHESTRATOR_CAN_KILL_ITSELF_OR_ITS_VAPP)

    def _check_keep_running(self, keep_running):
        return keep_running in self.KEEP_RUNNING_VALUES

    def need_to_stop_images(self, ignore_on_success_run_forever=False):
        runParameters = self._get_run_parameters()

        keep_running = runParameters.get('General.keep-running')

        if not self._check_keep_running(keep_running):
            message = 'Wrong value for "keep-running" (%s). Should be one of the following: %s. Using the default value (%s).'\
                    % (keep_running, self.KEEP_RUNNING_VALUES, self.KEEP_RUNNING_DEFAULT)
            util.printError(message)
            self.fail(message)
            keep_running = self.KEEP_RUNNING_DEFAULT

        stop = True
        if self.isAbort():
            if keep_running in [self.KEEP_RUNNING_ALWAYS, self.KEEP_RUNNING_ON_ERROR]:
                stop = False
        elif keep_running in [self.KEEP_RUNNING_ALWAYS, self.KEEP_RUNNING_ON_SUCCESS] and not ignore_on_success_run_forever:
            stop = False

        return stop

    def _update_slipstream_image(self, node_instance, new_image_id):
        util.printStep("Updating SlipStream image run")

        url = '%s/%s' % (node_instance.get_image_resource_uri(),
                         self._get_cloud_service_name())
        self._put_new_image_id(url, new_image_id)

    def complete_state_for_failed_node_instances(self):
        for node_instance_name in self._instance_names_force_to_compete_states:
            self.complete_state(node_instance_name)

    def delete_instances_from_run_server_side(self, instances_to_delete):
        """
        'instances_to_delete' dict : {'node_name' : [NodeInstance, ], }
        """
        ids_per_node_to_remove = {}
        for node_name, instances in instances_to_delete.iteritems():
            if len(instances) > 0:
                ids = map(lambda x: x.get_id(), instances)
                ids_per_node_to_remove.setdefault(node_name, []).extend(ids)
        self._delete_instances_from_run_server_side(ids_per_node_to_remove)

    def _delete_instances_from_run_server_side(self, ids_per_node):
        """'ids_per_node' dict : {'node_name': [id,], }
        """
        for node_name, ids in ids_per_node.iteritems():
            self._log_and_set_statecustom('Requesting to terminate and remove instances: (%s: %s)' %
                                          (node_name, sorted(map(int, ids))))
            self._ss_client.remove_instances_from_run(node_name, ids, detele_ids_only=True)

    def _get_node_instance_names_from_nodes_dict(self, nodes_dict):
        """Return list of the instance names [str, ].
        'nodes_dict' dict : {'node_name' : [NodeInstance, ], }
        """
        node_instances = util.flatten_list_of_lists(nodes_dict.values())
        return [x.get_name() for x in node_instances]

    @staticmethod
    def _get_node_instance_names_from_nodeinstances_dict(nodeinstances_dict):
        """Return list of the instance names [str, ].
        'nodeinstances_dict' dict : {<node_instance_name>: NodeInstance, }
        """
        return [x.get_name() for x in nodeinstances_dict.values()]

    #
    # Vertical Scaling
    #
    def vertically_scale_instances(self):

        scale_state = self._get_global_scale_state()
        if scale_state not in self.SCALE_STATES_VERTICAL_SCALABILITY:
            raise ExecutionException('Wrong scale state \'%s\' for vertical scalability (expected one of: %s)' %
                                     (scale_state, self.SCALE_STATES_VERTICAL_SCALABILITY))
        node_instances = self.get_node_instances_in_scale_state(scale_state).values()

        # wait pre.scale.done == True on all instances that are being scaled.
        self._wait_pre_scale_done(node_instances)

        # Request IaaS scaling action on each VMs being scaled and
        # set 'scale.iaas.done' to 'true' on each node instance when done.
        self._request_iaas_scaling_action(node_instances, scale_state)

        self._wait_scale_state(self.SCALE_STATES_START_STOP_MAP[scale_state], node_instances)

        # Unset scale.iaas.done for the synchronization to work next time.
        for node_instance in node_instances:
            self.unset_scale_iaas_done(node_instance)

    def _request_iaas_scaling_action(self, node_instances, scale_state):
        """
        :param node_instances:  list of node instances
        :type node_instances: list [NodeInstance, ]
        :param scale_state: scale state the instances are in
        :type scale_state: str
        """
        if scale_state == self.SCALE_STATE_RESIZING:
            self._cloud_client.resize(
                node_instances, done_reporter=self.set_scale_iaas_done)
        elif scale_state == self.SCALE_STATE_DISK_ATTACHING:
            self._cloud_client.attach_disk(
                node_instances, done_reporter=self.set_scale_iaas_done_and_set_attached_disk)
        elif scale_state == self.SCALE_STATE_DISK_DETACHING:
            self._cloud_client.detach_disk(
                node_instances, done_reporter=self.set_scale_iaas_done)

    def _wait_pre_scale_done(self, node_instances):
        """Blocking wait (with timeout) until RTP pre.scale.done is set on the requested node instances.
        :param node_instances: list of NodeInstance object to wait the RTP is set on
        :type node_instances: list [NodeInstance, ]
        :raises: TimeoutException
        """
        timeout_at = self._get_state_timeout_time()
        self._log('Waiting for node instances to finish pre-scaling before %s' %
                  util.toTimeInIso8601(timeout_at))

        self._wait_rtp_equals(node_instances, NodeDecorator.PRE_SCALE_DONE_SUCCESS,
                              self.get_pre_scale_done, timeout_at)

        self._log('All node instances finished pre-scaling.')

    def _wait_scale_state(self, state, node_instances):
        """Blocking wait (with timeout) until the state is set on the requested node instances.
        :param state: state to wait for
        :type state: string
        :param node_instances: list of NodeInstance object to wait the state on
        :type node_instances: list [NodeInstance, ]
        :raises: TimeoutException
        """
        timeout_at = self._get_state_timeout_time()
        self._log("Waiting for node instances to set '%s' to '%s' before %s" %
                  (NodeDecorator.SCALE_STATE_KEY, state, util.toTimeInIso8601(timeout_at)))

        self._wait_rtp_equals(node_instances, state, self._get_effective_scale_state,
                              timeout_at)

        self._log("All node instances set '%s' to '%s'." % (NodeDecorator.SCALE_STATE_KEY, state))


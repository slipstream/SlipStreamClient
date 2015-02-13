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

    def __init__(self, configHolder):
        super(CloudWrapper, self).__init__(configHolder)

        self._instance_names_to_be_gone = []

        # Explicitly call initCloudConnector() to set the cloud connector.
        self._cloud_client = None
        self.configHolder = configHolder
        self.imagesStopped = False

        self._instance_names_force_to_compete_states = []

    def initCloudConnector(self, configHolder=None):
        self._cloud_client = CloudConnectorFactory.createConnector(configHolder or self.configHolder)

    def build_image(self):
        self._cloud_client.set_slipstream_client_as_listener(self.get_slipstream_client())
        user_info = self._get_user_info(self._get_cloud_service_name())

        node_instance = self._get_node_instances_to_start().get(NodeDecorator.MACHINE_NAME)
        if node_instance is None:
            raise ExecutionException('Failed to get node instance for instance named "%s"' %
                                     NodeDecorator.MACHINE_NAME)

        new_id = self._cloud_client.build_image(user_info, node_instance)

        self._update_slipstream_image(node_instance, new_id)

    def start_node_instances(self):
        user_info = self._get_user_info(self._get_cloud_service_name())
        nodes_instances = self._get_node_instances_to_start()
        self._cloud_client.start_nodes_and_clients(user_info, nodes_instances)

        user_timeout_min = int(user_info.get_general('Timeout', self.WAIT_INSTANCES_PROVISIONED_MIN))
        # Wait less than defined by user.
        timeout_min = int(user_timeout_min * self.WAIT_TIME_PERCENTAGE)

        self._check_provisioning(nodes_instances.values(), timeout_min)

    def _check_provisioning(self, node_instances, timeout_min):
        """
        node_instances list [NodeInstance, ]
        """
        allowed_failed_vms_per_node = self._get_allowed_provisioning_failures_per_node(node_instances)

        if self._need_to_wait_instances_provisioned(allowed_failed_vms_per_node):
            all_provisioned = self._sleep_while_instances_provisioned(
                timeout_min, node_instances, allowed_failed_vms_per_node)
            if not all_provisioned and not self.isAbort():
                self._check_instances_provisioned(node_instances, allowed_failed_vms_per_node)
            else:
                self._log_and_set_statecustom('All instances were provisioned. Moving on.')

    def _need_to_wait_instances_provisioned(self, allowed_failed_vms_per_node):
        """
        allowed_failed_vms_per_node dict : {'node_name': integer, }
        """
        return max(allowed_failed_vms_per_node.values()) > 0

    def _sleep_while_instances_provisioned(self, sleep_time, node_instances, allowed_failed_vms_per_node):
        """
        sleep_time in min.
        node_instances list [NodeInstance, ]
        allowed_failed_vms_per_node dict : {'node_name': integer, }

        Return True if all it was detected that all instances were provisioned,
        False otherwise.

        """
        self._log('Waiting for %s min for %s instances to be provisioned.' %
                  (sleep_time, len(node_instances)))
        self._log('Allowed number of failed instances per node: %s' %
                  allowed_failed_vms_per_node)
        all_provisioned = False
        time_wait_max = time.time() + sleep_time * 60
        i = 1
        while time.time() < time_wait_max:
            time.sleep(30)
            if self.isAbort():
                self._log_and_set_statecustom('Abort flag detected. Stop waiting for '
                                              'instances to be provisioned.')
                break
            if self._all_provisioned(node_instances):
                all_provisioned = True
                self._log_and_set_statecustom('All instances provisioned. Exiting waiting loop.')
                break
            if i % 4 == 0:
                self._log_and_set_statecustom('Checking for VMs failed on IaaS level.')
                instances_failed_iaas = self._get_failed_instances_on_iaas(node_instances)
                if instances_failed_iaas:
                    instance_names = self._get_node_instance_names_from_nodes_dict(instances_failed_iaas)
                    self._log_and_set_statecustom('Failed on IaaS: %s' % instance_names)
                    self._check_too_many_failures(allowed_failed_vms_per_node,
                                                  instances_failed_iaas, 'IaaS')
            i += 1

        return all_provisioned

    def _all_provisioned(self, node_instances):
        self.clean_local_cache()
        return (len(self._get_creating_node_instances()) == 0) and True or False

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

        # Register instances to for forceful state completion.
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
            vm_id = self._cloud_client._vm_get_id(vm)
            if (vm_id in vm_ids) and self._cloud_client._has_vm_failed(vm):
                instance = vm_id_to_instance[vm_id]
                failed_instances.setdefault(instance.get_node_name(), []).append(instance)
        return failed_instances

    def _get_creating_node_instances(self):
        """Return dict {'node_name': [NodeInstance, ], } of instances that
        hasn't reported back to SlipStream server.
        """
        instances = self.get_node_instances_in_scale_state(
            self.SCALE_STATE_CREATING, self._get_cloud_service_name())
        creating_instances = {}
        for instance in instances.values():
            creating_instances.setdefault(instance.get_node_name(), []).append(instance)
        return creating_instances

    def _get_node_instances_to_start(self):
        return self.get_node_instances_in_scale_state(
            self.SCALE_STATE_CREATING, self._get_cloud_service_name())

    def _get_node_instances_to_stop(self):
        return self.get_node_instances_in_scale_state(
            self.SCALE_STATE_REMOVING, self._get_cloud_service_name())

    def stop_node_instances(self):
        node_instances_to_stop = self._get_node_instances_to_stop()
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

    def need_to_stop_images(self, ignore_on_success_run_forever=False):
        runParameters = self._get_run_parameters()

        onErrorRunForever = runParameters.get('General.On Error Run Forever', 'false')
        onSuccessRunForever = runParameters.get('General.On Success Run Forever', 'false')

        stop = True
        if self.isAbort():
            if onErrorRunForever == 'true':
                stop = False
        elif onSuccessRunForever == 'true' and not ignore_on_success_run_forever:
            stop = False

        return stop

    def _update_slipstream_image(self, node_instance, new_image_id):
        util.printStep("Updating SlipStream image run")

        url = '%s/%s' % (node_instance.get_image_resource_uri(),
                         self._get_cloud_service_name())
        self._put_new_image_id(url, new_image_id)

    def _get_cloud_service_name(self):
        return self._cloud_client.get_cloud_service_name()

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
            self._log_and_set_statecustom('Requesting to remove instance ids: (%s, %s)' % (node_name, ids))
            self._ss_client.remove_instances_from_run(node_name, ids, detele_ids_only=True)

    def _get_node_instance_names_from_nodes_dict(self, nodes_dict):
        """Return list of the instance names [str, ].
        'nodes_dict' dict : {'node_name' : [NodeInstance, ], }
        """
        node_instances = util.flatten_list_of_lists(nodes_dict.values())
        return [x.get_name() for x in node_instances]

    def _log_and_set_statecustom(self, msg):
        self._log(msg)
        try:
            self.set_statecustom(msg)
        except Exception as ex:
            self._log('Failed to set statecustom with: %s' % str(ex))

    def _log(self, msg):
        util.printDetail(msg, verboseThreshold=0)

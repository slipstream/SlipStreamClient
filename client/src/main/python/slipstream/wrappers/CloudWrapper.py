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

from slipstream.wrappers.BaseWrapper import BaseWrapper
from slipstream.cloudconnectors.CloudConnectorFactory import CloudConnectorFactory
from slipstream import util
from slipstream.util import deprecated
from slipstream.NodeDecorator import NodeDecorator


class CloudWrapper(BaseWrapper):

    def __init__(self, configHolder):
        super(CloudWrapper, self).__init__(configHolder)

        self._nodes_info = {}
        self._instance_names_to_be_gone = []

        # Explicitly call initCloudConnector() to set the cloud connector.
        self.cloudProxy = None
        self.configHolder = configHolder
        self.instancesDetail = []
        self.imagesStopped = False

    def initCloudConnector(self, configHolder=None):
        self.cloudProxy = CloudConnectorFactory. \
            createConnector(configHolder or self.configHolder)

    def publishDeploymentInitializationInfo(self):
        for instanceDetail in self.instancesDetail:
            for nodename, parameters in instanceDetail.items():
                self.publishNodeInitializationInfo(nodename,
                                                   str(parameters['id']),
                                                   parameters['ip'])

    def startImage(self):
        self.cloudProxy.setSlipStreamClientAsListener(self.clientSlipStream)
        userInfo, imageInfo = self._getUserAndImageInfo()
        self.instancesDetail = self.cloudProxy.startImage(userInfo, imageInfo)

    def buildImage(self):
        self.cloudProxy.setSlipStreamClientAsListener(self.clientSlipStream)
        userInfo, imageInfo = self._getUserAndImageInfo()
        self.cloudProxy.buildImage(userInfo, imageInfo)

    def start_node_instances(self):
        userInfo = self.getUserInfo(self.cloudProxy.cloud)
        nodes = self._get_node_instances_to_start()
        self.instancesDetail = self.cloudProxy.startNodesAndClients(
            userInfo, nodes)

    def _getUserAndImageInfo(self):
        return self.getUserInfo(self.cloudProxy.cloud), self.getImageInfo()

    def _get_node_instances_to_gone(self):
        return self._get_node_instances_in_scale_state(self.SCALE_STATE_REMOVED)

    def _get_node_instances_to_start(self):
        return self._get_node_instances_in_scale_state(self.SCALE_STATE_CREATING)

    def _get_node_instances_to_stop(self):
        return self._get_node_instances_in_scale_state(self.SCALE_STATE_REMOVING)

    def _get_node_instances_in_scale_state(self, scale_state):
        instances = {}
        for instance_name, instance in self._get_nodes_instances(self.cloudProxy.cloud).iteritems():
            if instance.get(NodeDecorator.SCALE_STATE_KEY, None) == scale_state:
                instances[instance_name] = instance
        return instances

    def stop_node_instances(self):
        ids = []
        node_instances_to_stop = self._get_node_instances_to_stop()
        for instance in node_instances_to_stop.values():
            ids.append(instance[NodeDecorator.INSTANCEID_KEY])
        self.cloudProxy.stopVmsByIds(ids)

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
        if self.needToStopImages(True):
            creator_id = self.getCreatorVmId()
            if creator_id:
                if not self.cloudProxy.hasCapability(self.cloudProxy.CAPABILITY_VAPP):
                    self.cloudProxy.stopVmsByIds([creator_id])
                elif not self.cloudProxy.hasCapability(self.cloudProxy.CAPABILITY_BUILD_IN_SINGLE_VAPP):
                    self.cloudProxy.stopVappsByIds([creator_id])

    def stopNodes(self):
        if self.needToStopImages():
            if not self.cloudProxy.hasCapability(self.cloudProxy.CAPABILITY_VAPP):
                self.cloudProxy.stopDeployment()
            self.imagesStopped = True

    def stopOrchestrator(self, is_build_image=False):
        if is_build_image:
            self.stopOrchestratorBuild()
        else:
            self.stopOrchestratorDeployment()

    def stopOrchestratorBuild(self):
        if self.needToStopImages(True):
            orch_id = self.getMachineCloudInstanceId()

            if self.cloudProxy.hasCapability(self.cloudProxy.CAPABILITY_VAPP):
                if self.cloudProxy.hasCapability(self.cloudProxy.CAPABILITY_ORCHESTRATOR_CAN_KILL_ITSELF_OR_ITS_VAPP):
                    if self.cloudProxy.hasCapability(self.cloudProxy.CAPABILITY_BUILD_IN_SINGLE_VAPP):
                        self.cloudProxy.stopDeployment()
                    else:
                        self.cloudProxy.stopVappsByIds([orch_id])
                else:
                    self.terminateRunServerSide()
            else:
                if self.cloudProxy.hasCapability(self.cloudProxy.CAPABILITY_ORCHESTRATOR_CAN_KILL_ITSELF_OR_ITS_VAPP):
                    self.cloudProxy.stopVmsByIds([orch_id])
                else:
                    self.terminateRunServerSide()

    def stopOrchestratorDeployment(self):
        if self.cloudProxy.hasCapability(self.cloudProxy.CAPABILITY_VAPP) and self.needToStopImages():
            if self.cloudProxy.hasCapability(self.cloudProxy.CAPABILITY_ORCHESTRATOR_CAN_KILL_ITSELF_OR_ITS_VAPP):
                self.cloudProxy.stopDeployment()
            else:
                self.terminateRunServerSide()
        elif self.needToStopImages() and not self.cloudProxy.hasCapability(self.cloudProxy.CAPABILITY_ORCHESTRATOR_CAN_KILL_ITSELF_OR_ITS_VAPP):
            self.terminateRunServerSide()
        else:
            orch_id = self.getMachineCloudInstanceId()
            self.cloudProxy.stopVmsByIds([orch_id])

    def terminateRunServerSide(self):
        self._deleteRunResource()

    def needToStopImages(self, ignore_on_success_run_forever=False):
        runParameters = self.getRunParameters()

        onErrorRunForever = runParameters.get('General.On Error Run Forever', 'false')
        onSuccessRunForever = runParameters.get('General.On Success Run Forever', 'false')

        stop = True
        if self.isAbort():
            if onErrorRunForever == 'true':
                stop = False
        elif onSuccessRunForever == 'true' and not ignore_on_success_run_forever:
            stop = False

        return stop

    def updateSlipStreamImage(self):
        util.printStep("Updating SlipStream image run")

        image_info = self.getImageInfo()

        newImageId = self.cloudProxy.getNewImageId()

        if not newImageId:
            return

        self._updateSlipStreamImage(self.cloudProxy.getResourceUri(image_info), newImageId)

    # REMARK: LS: I think it's a better idea to create a dedicated function in the cloud connector
    def _updateSlipStreamImage(self, resourceUri, newImageId):
        resourceUri = '%s/%s' % (resourceUri, self.getCloudInstanceName())
        self.putNewImageId(resourceUri, newImageId)

    def getCreatorVmId(self):
        return self.cloudProxy.getCreatorVmId()

    def getCloudName(self):
        return self.cloudProxy.cloudName

    def getCloudInstanceName(self):
        return self.cloudProxy.cloud

    def discard_nodes_info_locally(self):
        self._nodes_info = {}

    def _get_nodes_instances(self, cloud_service_name):
        '''Return dict {<node-name>: {<runtime-param-name>: <value>, }, }
        '''
        if not self._nodes_info:
            self._nodes_info = self.clientSlipStream.get_nodes_instances(cloud_service_name)
        return self._nodes_info

    @deprecated
    def isTerminateRunServerSide(self):
        return self.cloudProxy.isTerminateRunServerSide()

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


class CloudWrapper(BaseWrapper):
    def __init__(self, configHolder):
        super(CloudWrapper, self).__init__(configHolder)

        # Explicitly call initCloudConnector() to set the cloud connector.
        self.cloudProxy = None
        self.configHolder = configHolder
        self.instancesDetail = []
        self.imagesStopped = False

    def initCloudConnector(self, configHolder=None):
        self.cloudProxy = CloudConnectorFactory. \
            createConnector(configHolder or self.configHolder)

    # REMARK:
    #     LS: I think it's better to use a structure like the following
    #         {'noeudA': {'ip': 'ipA', 'id': 'idA'}, 'noeudB': {'ip': 'ipB', 'id': 'idB'}}
    #     instead of
    #         [{'noeudA': {'ip': 'ipA', 'id': 'idA'}}, {'noeudB': {'ip': 'ipB', 'id': 'idB'}}]
    #     so we can remove the first for loop
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

    def startImages(self):
        userInfo, nodes = self._getUserAndNodesInfo()

        defaultCloud = self.clientSlipStream.getDefaultCloudServiceName()
        nodesForThisOrchestrator = []
        for node in nodes:
            if (node['cloudService'] == self.cloudProxy.cloud or ((node['cloudService'] == 'default' or node[
                'cloudService'] == '' or node['cloudService'] == None) and self.cloudProxy.cloud == defaultCloud) ):
                nodesForThisOrchestrator.append(node)

        self.instancesDetail = self.cloudProxy.startNodesAndClients(userInfo, nodesForThisOrchestrator)

    def _getUserAndImageInfo(self):
        return self.getUserInfo(self.cloudProxy.cloud), self.getImageInfo()

    def _getUserAndNodesInfo(self):
        return self.getUserInfo(self.cloudProxy.cloud), self.getNodesInfo()

    def stopImages(self, ids=[], force=False):

        if self._needToStopImages() or force:
            if ids:
                self.cloudProxy.stopImagesByIds(ids)
            else:
                self.cloudProxy.stopImages()
            self.imagesStopped = True

    def terminateRunServerSide(self, force=False):
        if self._needToStopImages() or force:
            self._deleteRunResource()

    def _needToStopImages(self):
        userInfo = self.getUserInfo(self.cloudProxy.cloud)

        try:
            onErrorRunForever = userInfo.get_general('On Error Run Forever')
        except KeyError:
            onErrorRunForever = 'false'
        try:
            onSuccessRunForever = userInfo.get_general('On Success Run Forever')
        except KeyError:
            onSuccessRunForever = 'false'

        stop = True
        if self.isAbort():
            if onErrorRunForever == 'true':
                stop = False
        elif onSuccessRunForever == 'true':
            stop = False

        return stop

    def publishDeploymentTerminateInfo(self):
        if self.imagesStopped:
            finalState = 'Shutdown'
        else:
            finalState = 'Running'

        for instanceDetail in self.instancesDetail:
            for nodename in instanceDetail:
                self.setStateMessage(nodename, finalState)

    def updateSlipStreamImage(self):
        util.printStep("Updating SlipStream image run")

        image_info = self.getImageInfo()

        newImageId = self.cloudProxy.getNewImageId()

        if not newImageId:
            return

        self._updateSlipStreamImage(self.cloudProxy.getResourceUri(image_info),
                                    newImageId)

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

    def isTerminateRunServerSide(self):
        return self.cloudProxy.isTerminateRunServerSide()

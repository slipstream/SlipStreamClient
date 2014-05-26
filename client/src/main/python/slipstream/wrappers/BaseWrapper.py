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
    def __init__(self, configHolder):
        self.clientSlipStream = SlipStreamHttpClient(configHolder)
        self.clientSlipStream.ignoreAbort = True
        self.configHolder = configHolder

        self._userInfo = None
        self._imageInfo = None
        self._nodesInfo = None
        self._runParameters = None

    def advance(self):
        nodeName = self._getNodeName()
        self.clientSlipStream.advance(nodeName)

    def reset(self):
        self.clientSlipStream.reset()

    def fail(self, message):
        util.printError('Failing... %s' % message)
        traceback.print_exc()
        abort = self._qualifyKey(NodeDecorator.ABORT_KEY)
        self.clientSlipStream.setRuntimeParameter(abort, message)

    def getState(self):
        key = NodeDecorator.globalNamespacePrefix + NodeDecorator.STATE_KEY
        return self.clientSlipStream.getRuntimeParameter(key)

    def isAbort(self):
        key = NodeDecorator.globalNamespacePrefix + NodeDecorator.ABORT_KEY
        try:
            value = self.clientSlipStream.getRuntimeParameter(key, True)
        except NotYetSetException:
            value = ''
        return (value and True) or False

    def getRunCategory(self):
        return self.clientSlipStream.getRunCategory()

    def getRunType(self):
        return self.clientSlipStream.getRunType()

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

        _key = self._getNodeName() + NodeDecorator.NODE_PROPERTY_SEPARATOR + _key

        return _key

    def _getNodeName(self):
        return self.configHolder.nodename

    def nodename(self):
        return self._getNodeName()

    def getTargets(self):
        return self.clientSlipStream.getNodeDeploymentTargets()

    def getMachineCloudInstanceId(self):
        key = self._qualifyKey('instanceid')
        return self.clientSlipStream.getRuntimeParameter(key)

    def getRunResourceUri(self):
        return self.clientSlipStream.runInstanceEndpoint

    def _deleteRunResource(self):
        self.clientSlipStream._httpDelete(self.getRunResourceUri())

    def getUserInfo(self, cloud_service_name):
        if self._userInfo is None:
            self._userInfo = self.clientSlipStream.getUserInfo(cloud_service_name)
        return self._userInfo

    def getRunParameters(self):
        if self._runParameters is None:
            self._runParameters = self.clientSlipStream.getRunParameters()
        return self._runParameters

    def getImageInfo(self):
        if self._imageInfo is None:
            self._imageInfo = self.clientSlipStream.getImageInfo()
        return self._imageInfo

    def getNodesInfo(self):
        if self._nodesInfo is None:
            self._nodesInfo = self.clientSlipStream.getNodesInfo()
        return self._nodesInfo

    def getUserSshPubkey(self):
        userInfo = self.getUserInfo('')
        return userInfo.get_general('ssh.public.key')

    def putNewImageId(self, resourceUri, newImageId):
        self.clientSlipStream.putNewImageId(resourceUri, newImageId)

    def publishNodeInitializationInfo(self, nodename, vm_id, vm_ip):
        self.setInstanceId(nodename, vm_id)
        self.setInstanceIp(nodename, vm_ip)

    def setStateMessage(self, nodename, state):
        self._setRuntimeParameter(nodename, 'statemessage', state)

    def setInstanceId(self, nodename, vm_id):
        self._setRuntimeParameter(nodename, 'instanceid', vm_id)

    def setInstanceIp(self, nodename, vm_ip):
        self._setRuntimeParameter(nodename, 'hostname', vm_ip)

    def _setRuntimeParameter(self, nodename, key, value):
        parameter = nodename + NodeDecorator.NODE_PROPERTY_SEPARATOR + key
        self.clientSlipStream.setRuntimeParameter(parameter, value)

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
    # FIXME: rename me please
    SCALE_STATE_OPERATIONAL = 'operational'

    SCALE_STATE_REMOVING = 'removing'
    SCALE_STATE_REMOVED = 'removed'
    SCALE_STATE_GONE = 'gone'

    def __init__(self, configHolder):
        self.clientSlipStream = SlipStreamHttpClient(configHolder)
        self.clientSlipStream.set_http_max_retries(self.is_mutable() and -5 or 5)
        self.clientSlipStream.ignoreAbort = True
        self.configHolder = configHolder

        self._userInfo = None
        self._imageInfo = None
        self._runParameters = None

    def complete_state(self):
        nodeName = self._getNodeName()
        self.clientSlipStream.complete_state(nodeName)

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

    def get_run_category(self):
        return self.clientSlipStream.get_run_category()

    def get_run_type(self):
        return self.clientSlipStream.get_run_type()

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
        return self.clientSlipStream.get_node_deployment_targets()

    def get_cloud_instance_id(self):
        key = self._qualifyKey(NodeDecorator.INSTANCEID_KEY)
        return self.clientSlipStream.getRuntimeParameter(key)

    def discard_user_info_locally(self):
        self._userInfo = None

    def get_user_info(self, cloud_service_name):
        if self._userInfo is None:
            self._userInfo = self.clientSlipStream.get_user_info(cloud_service_name)
        return self._userInfo

    def get_run_parameters(self):
        if self._runParameters is None:
            self._runParameters = self.clientSlipStream.get_run_parameters()
        return self._runParameters

    def get_user_ssh_pubkey(self):
        userInfo = self.get_user_info('')
        return userInfo.get_public_keys()

    def need_to_stop_images(self, ignore_on_success_run_forever=False):
        # pylint: disable=unused-argument
        return False

    def is_mutable(self):
        mutable = self.clientSlipStream.get_run_mutable()
        return util.str2bool(mutable)

    def discard_run_locally(self):
        self.clientSlipStream.discard_run()

    def set_scale_state_on_node_instances(self, instance_names, scale_state):
        for instance_name in instance_names:
            key = instance_name + NodeDecorator.NODE_PROPERTY_SEPARATOR + NodeDecorator.SCALE_STATE_KEY
            self.clientSlipStream.setRuntimeParameter(key, scale_state)

    def set_scale_state(self, scale_state):
        '''Set scale state for this node instances.
        '''
        key = self._qualifyKey(NodeDecorator.SCALE_STATE_KEY)
        self.clientSlipStream.setRuntimeParameter(key, scale_state)

    def get_scale_state(self):
        '''Set scale state for this node instances.
        '''
        key = self._qualifyKey(NodeDecorator.SCALE_STATE_KEY)
        return self.clientSlipStream.getRuntimeParameter(key)

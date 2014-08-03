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
from __future__ import print_function

import os

import slipstream.util as util
import slipstream.exceptions.Exceptions as Exceptions

from slipstream.UserInfo import UserInfo
from slipstream.HttpClient import HttpClient
from slipstream.NodeInstance import NodeInstance
from slipstream.NodeDecorator import NodeDecorator

etree = util.importETree()


class SlipStreamHttpClient(object):
    URL_IGNORE_ABORT_ATTRIBUTE_QUERY = '?ignoreabort=true'

    def __init__(self, configHolder):
        self.category = None
        self.run_dom = None
        self.ignoreAbort = False
        self.username = ''
        self.diid = ''
        self.nodename = ''
        self.serviceurl = ''
        self.verboseLevel = None
        self.http_max_retries = 2

        configHolder.assign(self)
        self._assemble_endpoints()
        self.httpClient = HttpClient(configHolder=configHolder)

    def set_http_max_retries(self, http_max_retries):
        self.http_max_retries = http_max_retries

    def _assemble_endpoints(self):
        self.runEndpoint = self.serviceurl + util.RUN_RESOURCE_PATH
        self.run_url = self.runEndpoint + '/' + self.diid

        self.authnServiceUrl = self.serviceurl + '/'

        self.runReportEndpoint = '%s/reports/%s' % (self.serviceurl,
                                                    self.diid)

        self.userEndpoint = '%s/user/%s' % (self.serviceurl,
                                            self.username)

    def get_user_info(self, cloud_qualifier):

        dom = self._getUserElement()

        userInfo = UserInfo(cloud_qualifier)

        userInfo['User.firstName'] = dom.attrib['firstName']
        userInfo['User.lastName'] = dom.attrib['lastName']
        userInfo['User.email'] = dom.attrib['email']

        parameters = dom.findall('parameters/entry/parameter')
        for param in parameters:
            if param.attrib['category'] in ['General', cloud_qualifier]:
                name = param.attrib['name']
                userInfo[name] = param.findtext('value')

        return userInfo

    def _getUserElement(self):
        content = self._getUserContent()

        return etree.fromstring(content)

    def _getUserContent(self):
        url = self.userEndpoint
        _, content = self._httpGet(url, 'application/xml')
        return content

    def get_node_deployment_targets(self):
        self._retrieveAndSetRun()
        return DomExtractor.get_deployment_targets(self.run_dom,
                                                 self._getGenericNodename())

    def _extractModuleResourceUri(self, run):
        rootElement = etree.fromstring(run)
        return rootElement.attrib[NodeDecorator.MODULE_RESOURCE_URI]

    def get_nodes_instances(self, cloud_service_name=None):
        '''Return dict {<nodename>: NodeInstance, }
        '''
        nodes_instances = {}

        self._retrieveAndSetRun()
        nodes_instances_runtime_parameters = \
            DomExtractor.extract_nodes_instances_runtime_parameters(
                self.run_dom, cloud_service_name)

        for node_instance_name, node_instance_runtime_parameters in nodes_instances_runtime_parameters.items():

            node_instance = NodeInstance(node_instance_runtime_parameters)
            node_name = node_instance.get_node_name()

            image_attributes = DomExtractor.extract_node_image_attributes(self.run_dom, node_name)
            node_instance.set_image_attributes(image_attributes)

            if not node_instance.is_orchestrator():
                image_targets = DomExtractor.extract_node_image_targets(self.run_dom, node_name)
                node_instance.set_image_targets(image_targets)

            nodes_instances[node_instance_name] = node_instance

        return nodes_instances

    def _getGenericNodename(self):
        'Nodename w/o multiplicity'
        return self.nodename.split(NodeDecorator.NODE_MULTIPLICITY_SEPARATOR)[0]

    def get_run_category(self):
        self._retrieveAndSetRun()
        return DomExtractor.extractCategoryFromRun(self.run_dom)

    def get_run_type(self):
        self._retrieveAndSetRun()
        return DomExtractor.extractTypeFromRun(self.run_dom)

    def get_run_mutable(self):
        self._retrieveAndSetRun()
        return DomExtractor.extract_mutable_from_run(self.run_dom)

    def discard_run(self):
        self.run_dom = None

    def _retrieveAndSetRun(self):
        if self.run_dom is None:
            url = self.run_url
            _, run = self._retrieve(url)
            self.run_dom = etree.fromstring(run)

    def _retrieve(self, url):
        return self._httpGet(url, 'application/xml')

    def reset(self):
        url = self.run_url
        self._httpPost(url, 'reset', 'text/plain')

    def execute(self, resourceUri):
        url = self.runEndpoint
        return self._httpPost(url, resourceUri, 'text/plain')

    def complete_state(self, nodeName):
        url = '%s/%s:%s' % (self.run_url, nodeName,
                            NodeDecorator.COMPLETE_KEY)
        url += SlipStreamHttpClient.URL_IGNORE_ABORT_ATTRIBUTE_QUERY
        return self._httpPost(url, 'reset', 'text/plain')

    def terminate_run(self):
        return self._httpDelete(self.run_url)

    def _fail(self, message):
        self.setRuntimeParameter(
            NodeDecorator.globalNamespacePrefix + NodeDecorator.ABORT_KEY, message)

    def sendReport(self, report):
        self._uploadReport(self.runReportEndpoint, report)

    def _uploadReport(self, url, report):
        print('Uploading report to: %s' % url)

        body = open(report, 'rb').read()
        url += '/' + os.path.basename(report)

        self._httpPut(url, body, '', accept="*/*")

    def isAbort(self):
        return self.getGlobalAbortMessage() != ''

    def getGlobalAbortMessage(self):
        url = '%s/%s%s' % (self.run_url,
                           NodeDecorator.globalNamespacePrefix,
                           NodeDecorator.ABORT_KEY)
        url += SlipStreamHttpClient.URL_IGNORE_ABORT_ATTRIBUTE_QUERY
        _, content = self._httpGet(url, accept='text/plain')
        return content.strip().strip('"').strip("'")

    def get_run_parameters(self):
        self._retrieveAndSetRun()
        return DomExtractor.extract_run_parameters_from_run(self.run_dom)

    def getRuntimeParameter(self, key, ignoreAbort=False):

        url = self.run_url + '/' + key
        if (self.ignoreAbort or ignoreAbort):
            url += SlipStreamHttpClient.URL_IGNORE_ABORT_ATTRIBUTE_QUERY
        try:
            _, content = self._httpGet(url, accept='text/plain')
        except Exceptions.NotFoundError, ex:
            raise Exceptions.NotFoundError('"%s" for %s' % (str(ex), key))

        return content.strip().strip('"').strip("'")

    def setRuntimeParameter(self, key, value, ignoreAbort=False):
        url = self.run_url + '/' + key
        if self.ignoreAbort or ignoreAbort:
            url += SlipStreamHttpClient.URL_IGNORE_ABORT_ATTRIBUTE_QUERY

        _, content = self._httpPut(url, util.removeASCIIEscape(value),
                                   accept='text/plain')

        return content.strip().strip('"').strip("'")

    def _httpGet(self, url, accept='application/xml'):
        return self.httpClient.get(url, accept, retry_number=self.http_max_retries)

    def _httpPut(self, url, body=None, contentType='application/xml', accept='application/xml'):
        return self.httpClient.put(url, body, contentType, accept, retry_number=self.http_max_retries)

    def _httpPost(self, url, body=None, contentType='application/xml'):
        return self.httpClient.post(url, body, contentType, retry_number=self.http_max_retries)

    def _httpDelete(self, url):
        return self.httpClient.delete(url, retry_number=self.http_max_retries)

    def _printDetail(self, message):
        util.printDetail(message, self.verboseLevel, util.VERBOSE_LEVEL_DETAILED)

    def put_new_image_id(self, image_resource_uri, image_id):
        url = self.serviceurl + '/' + image_resource_uri
        self._printDetail('Set new image id: %s %s' % (url, image_id))
        self._httpPut(url, image_id)

    def launchDeployment(self, params):
        body = '&'.join(params)
        resp, _ = self._httpPost(self.runEndpoint, body, contentType='text/plain')
        return resp['location']

    def getRunState(self, uuid=None, ignoreAbort=True):
        if not uuid and not self.diid:
            raise Exceptions.ExecutionException("Run ID should be provided "
                                                "to get state.")
        state_key = NodeDecorator.globalNamespacePrefix + NodeDecorator.STATE_KEY
        self.run_url = self.runEndpoint + '/' + (uuid or self.diid)
        return self.getRuntimeParameter(state_key, ignoreAbort=ignoreAbort)


class DomExtractor(object):
    EXTRADISK_PREFIX = 'extra.disk'
    EXTRADISK_VOLATILE_KEY = EXTRADISK_PREFIX + '.volatile'

    PATH_TO_NODE_ON_RUN = 'module/nodes/entry/node'
    PATH_TO_PARAMETER = 'parameters/entry/parameter'

    @staticmethod
    def extract_nodes_instances_runtime_parameters(run_dom, cloud_service_name=None):
        '''Return dict {<nodename>: {<runtimeparamname>: <value>, }, }
        '''
        nodes_instances = {}
        for node_instance_name in run_dom.attrib['nodeNames'].split(','):
            node_instance_name = node_instance_name.strip()

            if NodeDecorator.is_orchestrator_name(node_instance_name):
                continue

            node_instance = {}
            node_instance[NodeDecorator.NODE_INSTANCE_NAME_KEY] = node_instance_name

            # Unfortunately, this doesn't work on Python 2.6.6
            # query = "runtimeParameters/entry/runtimeParameter[@group='%s']" % node_instance_name
            query = "runtimeParameters/entry/runtimeParameter"
            for rtp in run_dom.findall(query):
                if rtp.get('group') == node_instance_name:
                    key = DomExtractor._get_key_from_runtimeparameter(rtp)
                    node_instance[key] = rtp.text
            nodes_instances[node_instance_name] = node_instance

        if cloud_service_name is not None:
            for node_instance_name in nodes_instances.keys():
                if cloud_service_name != nodes_instances[node_instance_name][NodeDecorator.CLOUDSERVICE_KEY]:
                    del nodes_instances[node_instance_name]

        return nodes_instances

    @staticmethod
    def _get_key_from_runtimeparameter(rtp):
        return rtp.attrib['key'].split(NodeDecorator.NODE_PROPERTY_SEPARATOR, 1)[-1]

    @staticmethod
    def extract_node_image_attributes(run_dom, nodename):
        ''' Return image attributes of all nodes.
        '''
        image = DomExtractor.extract_node_image(run_dom, nodename)
        attributes = {}

        if image is not None:
            attributes = DomExtractor.get_attributes(image)

        return attributes

    @staticmethod
    def extract_node_image(run_dom, nodename):
        ''' Return image attributes of all nodes.
        '''
        image = None

        if DomExtractor.get_module_category(run_dom) == NodeDecorator.IMAGE:
            image = run_dom.find('module')
        else:
            for node in run_dom.findall(DomExtractor.PATH_TO_NODE_ON_RUN):
                if node.get('name') == nodename:
                    image = node.find('image')

        return image

    @staticmethod
    def extract_node_image_targets(run_dom, node_name):
        targets = {}
        image_dom = DomExtractor.extract_node_image(run_dom, node_name)

        category = DomExtractor.get_module_category(run_dom)
        if category == NodeDecorator.IMAGE:
            targets = DomExtractor.get_build_targets(image_dom)
        elif category == NodeDecorator.DEPLOYMENT:
            targets = DomExtractor.get_deployment_targets_from_image(image_dom)
        else:
            raise Exceptions.ClientError("Unknown category: '%s'. Possible values: %s" %
                                         (category, [NodeDecorator.IMAGE, NodeDecorator.DEPLOYMENT]))

        return targets

    @staticmethod
    def get_module_category(run_dom):
        return run_dom.find('module').get('category')

    @staticmethod
    def get_extra_disks_from_image(image_dom):
        extra_disks = {}

        for entry in image_dom.findall('parameters/entry'):
            param_name = entry.find('parameter').get('name')
            if param_name.startswith(DomExtractor.EXTRADISK_PREFIX):
                try:
                    extra_disks[param_name] = entry.find('parameter/value').text or ''
                except AttributeError:
                    pass

        return extra_disks

    @staticmethod
    def get_element_value_from_element_tree(element_tree, element_name):
        element = element_tree.find(element_name)
        value = getattr(element, 'text', '')
        if value is None:
            value = ''
        return value

    @staticmethod
    def get_attributes(dom):
        return dom.attrib

    @staticmethod
    def get_build_targets(run_dom):
        targets = {}

        for target in ['prerecipe', 'recipe']:
            targets[target] = DomExtractor.get_element_value_from_element_tree(run_dom, target)

        targets['packages'] = []
        packages = run_dom.findall('packages/package')
        for package in packages:
            name = package.get('name')
            if name:
                targets['packages'].append(name)

        return targets

    @staticmethod
    def extractCategoryFromRun(run_dom):
        return run_dom.attrib['category']

    @staticmethod
    def extractTypeFromRun(run_dom):
        return run_dom.attrib['type']

    @staticmethod
    def extract_mutable_from_run(run_dom):
        return run_dom.attrib['mutable']

    @staticmethod
    def extractDefaultCloudServiceNameFromRun(run_dom):
        return run_dom.attrib['cloudServiceName']

    @staticmethod
    def extract_run_parameters_from_run(run_dom):
        parameters = {}
        for node in run_dom.findall(DomExtractor.PATH_TO_PARAMETER):
            value = node.find('value')
            parameters[node.get('name')] = value.text if value is not None else None
        return parameters

    @staticmethod
    def get_deployment_targets(run_dom, nodename):
        '''Return deployment targets from the image of the node 'nodename'.
        '''
        module = run_dom.find('module')

        if module.get('category') == 'Image':
            return DomExtractor.get_deployment_targets_from_image(module)
        else:
            for node in run_dom.findall(DomExtractor.PATH_TO_NODE_ON_RUN):
                if node.get('name') == nodename:
                    return DomExtractor.get_deployment_targets_from_image(node.find('image'))
        return {}

    @staticmethod
    def get_deployment_targets_from_image(image_dom):
        '''Return deployment targets of the given image.
        '''
        targets = {}
        for targetNode in image_dom.findall('targets/target'):
            runInBackgroundStr = targetNode.get('runInBackground')
            runInBackground = False
            if runInBackgroundStr:
                if runInBackgroundStr.lower() == 'true':
                    runInBackground = True
            targets[targetNode.get('name')] = (targetNode.text, runInBackground)
        return targets

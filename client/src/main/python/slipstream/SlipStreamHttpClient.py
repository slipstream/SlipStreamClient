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

from slipstream.NodeDecorator import NodeDecorator
import slipstream.exceptions.Exceptions as Exceptions
import slipstream.util as util
from slipstream.HttpClient import HttpClient

etree = util.importETree()


class UserInfo(dict):
    def __init__(self, cloud_qualifier):
        super(UserInfo, self).__init__({})
        self.cloud = cloud_qualifier + '.'
        self.user = 'User.'
        self.general = 'General.'
        self.qualifires = (self.cloud, self.user, self.general)

    def get_cloud(self, key):
        return self.__getitem__(self.cloud + key)

    def get_general(self, key):
        return self.__getitem__(self.general + key)

    def get_user(self, key):
        return self.__getitem__(self.user + key)

    def __setitem__(self, key, val):
        if not key.startswith(self.qualifires):
            raise ValueError('Key should start with one of: %s' %
                ', '.join(self.qualifires))
        dict.__setitem__(self, key, val)


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

        configHolder.assign(self)

        self._assembleEndpoints()

        self.httpClient = HttpClient(configHolder=configHolder)

    def _assembleEndpoints(self):
        self.serviceRootEndpoint = self.serviceurl

        self.runEndpoint = self.serviceRootEndpoint + util.RUN_URL_PATH
        self.runInstanceEndpoint = self.runEndpoint + '/' + self.diid

        self.authnServiceUrl = self.serviceRootEndpoint + '/'

        self.runReportEndpoint = '%s/reports/%s' % (self.serviceRootEndpoint,
                                                    self.diid)

        self.userEndpoint = '%s/user/%s' % (self.serviceRootEndpoint,
                                            self.username)

    def getUserInfo(self, cloud_qualifier):

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

    def getImageInfo(self):
        image_dom = self._getImageInfoDom()
        return self._getImageInfoFromImageDom(image_dom)

    def _getImageInfoFromImageDom(self, imageDom):
        info = {}
        info['attributes'] = DomExtractor.getAttributes(imageDom)
        info['targets'] = self._getTargets(imageDom)
        info['cloud_parameters'] = DomExtractor.getImageCloudParametersFromImageDom(imageDom)
        info['extra_disks'] = DomExtractor.getExtraDisksFromImageDom(imageDom)
        return info

    def _getImageInfoDom(self):
        return self.run_dom.find('module')

    def getNodeDeploymentTargets(self):
        self._retrieveAndSetRun()
        return DomExtractor.getDeploymentTargets(self.run_dom,
                                                 self._getGenericNodename())

    def _extractModuleResourceUri(self, run):
        rootElement = etree.fromstring(run)
        return rootElement.attrib[NodeDecorator.MODULE_RESOURCE_URI]

    def _extractRuntimeParameter(self, key, run):
        rootElement = etree.fromstring(run)
        return rootElement.attrib[NodeDecorator.MODULE_RESOURCE_URI]

    def getNodesInfo(self):
        self._retrieveAndSetRun()
        return self._getRemoteNodes()

    def _getRemoteNodes(self):
        nodes = DomExtractor.extractNodesFromRun(self.run_dom)
        for node in nodes:
            node['image'] = self._getImageInfoFromImageDom(node['image'])
        return nodes

    def _getTargets(self, image_dom):
        category = self.getRunCategory()
        if category == NodeDecorator.IMAGE:
            return DomExtractor.getBuildTargets(image_dom)
        if category == NodeDecorator.DEPLOYMENT:
            return DomExtractor.getDeploymentTargetsFromImageDom(image_dom)
        else:
            raise Exceptions.ClientError("Unknown category: %s" % category)

    def _getGenericNodename(self):
        'Nodename w/o multiplicity'
        return self.nodename.split(NodeDecorator.NODE_MULTIPLICITY_SEPARATOR)[0]

    def getRunCategory(self):
        return self._getRunCategory()

    def _getRunCategory(self):
        self._retrieveAndSetRun()
        return DomExtractor.extractCategoryFromRun(self.run_dom)

    def getRunType(self):
        return self._getRunType()

    def _getRunType(self):
        self._retrieveAndSetRun()
        return DomExtractor.extractTypeFromRun(self.run_dom)

    def getDefaultCloudServiceName(self):
        return self._getDefaultCloudServiceName()

    def _getDefaultCloudServiceName(self):
        self._retrieveAndSetRun()
        return DomExtractor.extractDefaultCloudServiceNameFromRun(self.run_dom)

    def _retrieveAndSetRun(self):
        if self.run_dom is None:
            url = self.runInstanceEndpoint
            _, run = self._retrieve(url)
            self.run_dom = etree.fromstring(run)

    def _retrieve(self, url):
        return self._httpGet(url, 'application/xml')

    def reset(self):
        url = self.runInstanceEndpoint
        self._httpPost(url, 'reset', 'text/plain')

    def execute(self, resourceUri):
        url = self.runEndpoint
        return self._httpPost(url, resourceUri, 'text/plain')

    def advance(self, nodeName):
        url = '%s/%s:%s' % (self.runInstanceEndpoint, nodeName,
                            NodeDecorator.STATE_KEY)
        url += SlipStreamHttpClient.URL_IGNORE_ABORT_ATTRIBUTE_QUERY
        return self._httpPost(url, 'reset', 'text/plain')

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
        url = '%s/%s%s' % (self.runInstanceEndpoint,
                           NodeDecorator.globalNamespacePrefix,
                           NodeDecorator.ABORT_KEY)
        url += SlipStreamHttpClient.URL_IGNORE_ABORT_ATTRIBUTE_QUERY
        _, content = self._httpGet(url, accept='text/plain')
        return content.strip().strip('"').strip("'")

    def getRunParameters(self):
        self._retrieveAndSetRun()
        return DomExtractor.extractRunParametersFromRun(self.run_dom)

    def getRuntimeParameter(self, key, ignoreAbort=False):

        url = self.runInstanceEndpoint + '/' + key
        if (self.ignoreAbort or ignoreAbort):
            url += SlipStreamHttpClient.URL_IGNORE_ABORT_ATTRIBUTE_QUERY
        try:
            _, content = self._httpGet(url, accept='text/plain')
        except Exceptions.NotFoundError, ex:
            raise Exceptions.NotFoundError('"%s" for %s' % (str(ex), key))

        return content.strip().strip('"').strip("'")

    def setRuntimeParameter(self, key, value, ignoreAbort=False):
        url = self.runInstanceEndpoint + '/' + key
        if self.ignoreAbort or ignoreAbort:
            url += SlipStreamHttpClient.URL_IGNORE_ABORT_ATTRIBUTE_QUERY

        _, content = self._httpPut(url, util.removeASCIIEscape(value),
                                   accept='text/plain')

        return content.strip().strip('"').strip("'")

    def _httpGet(self, url, accept='application/xml'):
        return self.httpClient.get(url, accept)

    def _httpPut(self, url, body=None, contentType='application/xml',
                 accept='application/xml'):
        return self.httpClient.put(url, body, contentType, accept)

    def _httpPost(self, url, body=None, contentType='application/xml'):
        return self.httpClient.post(url, body, contentType)

    def _httpDelete(self, url):
        return self.httpClient.delete(url)

    def _printDetail(self, message):
        util.printDetail(message, self.verboseLevel, util.VERBOSE_LEVEL_DETAILED)

    def putNewImageId(self, resourceUri, imageId):
        url = self.serviceRootEndpoint + '/' + resourceUri
        self._printDetail('Set new image id: %s %s' % (url, imageId))
        self._httpPut(url, imageId)

    def launchDeployment(self, params):
        body = '&'.join(params)
        resp, _ = self._httpPost(self.runEndpoint, body, contentType='text/plain')
        return resp['location']

    def getRunState(self, uuid=None, ignoreAbort=True):
        if not uuid and not self.diid:
            raise Exceptions.ExecutionException("Run ID should be provided "
                                                "to get state.")
        state_key = NodeDecorator.globalNamespacePrefix + NodeDecorator.STATE_KEY
        self.runInstanceEndpoint = self.runEndpoint + '/' + (uuid or self.diid)
        return self.getRuntimeParameter(state_key, ignoreAbort=ignoreAbort)


class DomExtractor(object):
    EXTRADISK_PREFIX = 'extra.disk'

    @staticmethod
    def extractNodesFromRun(run_dom):
        nodes = []
        for _node in run_dom.findall('module/nodes/entry/node'):
            node = {}
            node['cloudService'] = _node.get('cloudService')
            node['multiplicity'] = int(_node.get('multiplicity'))
            node['nodename'] = _node.get('name')
            node['image'] = _node.find('image')
            nodes.append(node)
        return nodes

    @staticmethod
    def getExtraDisksFromImageDom(image_dom):
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
    def getImageCloudParametersFromImageDom(image_dom):
        cloudParameters = {}
        parameters = image_dom.findall('parameters/entry/parameter')
        for param in parameters:
            category = param.attrib['category']
            if not category in ('Input', 'Output'):
                name = param.attrib['name']
                # extra disks go on the node level
                if not name.startswith(DomExtractor.EXTRADISK_PREFIX):
                    if category not in cloudParameters:
                        cloudParameters.update({category: {}})
                    cloudParameters[category][name] = param.findtext('value')

        return cloudParameters

    @staticmethod
    def getElementValueFromElementTree(elementTree, elementName):
        element = elementTree.find(elementName)
        value = getattr(element, 'text', '')
        if value is None:
            value = ''
        return value

    @staticmethod
    def getAttributes(dom):
        return dom.attrib

    @staticmethod
    def getBuildTargets(dom):
        targets = {}

        for target in ['prerecipe', 'recipe']:
            targets[target] = DomExtractor.getElementValueFromElementTree(dom,
                                                                          target)

        targets['packages'] = []
        packages = dom.findall('packages/package')
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
    def extractDefaultCloudServiceNameFromRun(run_dom):
        return run_dom.attrib['cloudServiceName']

    @staticmethod
    def extractRunParametersFromRun(run_dom):
        parameters = {}
        for node in run_dom.findall('parameters/entry/parameter'):
            value = node.find('value')
            parameters[node.get('name')] = value.text if value is not None else None
        return parameters

    @staticmethod
    def getDeploymentTargets(run_dom, nodename):
        "Get deployment targets for node with name 'nodename'"
        module = run_dom.find('module')

        if module.get('category') == 'Image':
            return DomExtractor.getDeploymentTargetsFromImageDom(module)
        else:
            for node in run_dom.findall('module/nodes/entry/node'):
                if node.get('name') == nodename:
                    return DomExtractor.getDeploymentTargetsFromImageDom(
                        node.find('image'))
        return {}

    @staticmethod
    def getDeploymentTargetsFromImageDom(image_dom):
        "Get deployment targets for the given image."
        targets = {}
        for targetNode in image_dom.findall('targets/target'):
            runInBackgroundStr = targetNode.get('runInBackground')
            runInBackground = False
            if runInBackgroundStr:
                if runInBackgroundStr.lower() == 'true':
                    runInBackground = True
            targets[targetNode.get('name')] = (targetNode.text, runInBackground)
        return targets

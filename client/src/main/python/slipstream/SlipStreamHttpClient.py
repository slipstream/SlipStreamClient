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

from slipstream.UserInfo import UserInfo
from slipstream.NodeInstance import NodeInstance
from slipstream.NodeDecorator import NodeDecorator
from slipstream.DomExtractor import DomExtractor

import time
import httplib
import requests
import socket
from random import random
from threading import Lock
from urlparse import urlparse
from requests.exceptions import RequestException
from requests.cookies import RequestsCookieJar

try:
    from requests.packages.urllib3.exceptions import HTTPError
except:
    from urllib3.exceptions import HTTPError

import slipstream.exceptions.Exceptions as Exceptions
import slipstream.util as util

from slipstream.api import Api

etree = util.importETree()


DEFAULT_SS_COOKIE_NAME = 'com.sixsq.slipstream.cookie'


def get_cookie(cookie_jar, domain, path=None, name=DEFAULT_SS_COOKIE_NAME):
    """Returns requested cookie from the provided cookie_jar."""
    jar = RequestsCookieJar()
    jar.update(cookie_jar)
    cookie = None
    if path is None:
        cookies = jar.get_dict(domain=domain)
        cookie = cookies.get(name)
    elif path == '/':
        cookies = jar.get_dict(domain=domain, path=path)
        cookie = cookies.get(name)
    else:
        url_path = path.split('/')
        for n in range(len(url_path), 0, -1):
            path = '/'.join(url_path[0:n]) or '/'
            cookies = jar.get_dict(domain=domain, path=path)
            if name in cookies:
                cookie = cookies.get(name)
                break
    if cookie is None:
        return cookie
    else:
        return '%s=%s' % (name, cookie)


# Client Error
NOT_FOUND_ERROR = 404
CONFLICT_ERROR = 409
PRECONDITION_FAILED_ERROR = 412
EXPECTATION_FAILED_ERROR = 417
TOO_MANY_REQUESTS_ERROR = 429
# Server Error
SERVICE_UNAVAILABLE_ERROR = 503


def http_debug():
    import logging
    from httplib import HTTPConnection

    HTTPConnection.debuglevel = 3

    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)

    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True


def disable_urllib3_warnings():
    try:
        requests.packages.urllib3.disable_warnings(
            requests.packages.urllib3.exceptions.InsecureRequestWarning)
    except:
        try:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        except:
            pass


class SlipStreamHttpClient(object):
    URL_IGNORE_ABORT_ATTRIBUTE_QUERY = '?ignoreabort=true'

    def __init__(self, configHolder):
        self.category = None
        self.run_dom = None
        self.ignoreAbort = False
        self.username = ''
        self.password = ''
        self.diid = ''
        self.node_instance_name = ''
        self.serviceurl = ''
        self.verboseLevel = util.VERBOSE_LEVEL_NORMAL
        self.cookie_filename = util.DEFAULT_COOKIE_FILE
        self.retry = True
        self.host_cert_verify = False

        configHolder.assign(self)
        self._assemble_endpoints()

        login_creds = self._get_login_creds()
        if not login_creds:
            self._log_normal('WARNING: No login credentials provided. '
                             'Assuming cookies from a persisted cookie-jar %s will be used.'
                             % self.cookie_filename)

        self.api = Api(endpoint=self.serviceurl, cookie_file=self.cookie_filename,
                       reauthenticate=True, login_creds=login_creds)

        self.lock = Lock()
        self.too_many_requests_count = 0

        if configHolder:
            configHolder.assign(self)

        if self.verboseLevel >= 3:
            http_debug()
        else:
            disable_urllib3_warnings()

        self.session = None

    def set_retry(self, retry):
        self.retry = retry

    def _assemble_endpoints(self):
        self.runEndpoint = self.serviceurl + util.RUN_RESOURCE_PATH
        self.run_url = self.runEndpoint + '/' + self.diid

        self.authnServiceUrl = self.serviceurl + '/api/session'

        self.runReportEndpoint = '%s/reports/%s' % (self.serviceurl,
                                                    self.diid)

        self.userEndpoint = '%s/user/%s' % (self.serviceurl,
                                            self.username)

        self.configuration_endpoint = '%s%s' % (self.serviceurl,
                                                util.CONFIGURATION_RESOURCE_PATH)

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
                userInfo[name] = param.findtext('value', '')

        return userInfo

    def _getUserElement(self):
        content = self._getUserContent()

        return etree.fromstring(content.encode('utf-8'))

    def _getUserContent(self):
        url = self.userEndpoint
        _, content = self._httpGet(url, 'application/xml')
        return content

    def _extractModuleResourceUri(self, run):
        rootElement = etree.fromstring(run.encode('utf-8'))
        return rootElement.attrib[NodeDecorator.MODULE_RESOURCE_URI]

    def get_nodes_instances(self, cloud_service_name=None):
        """Return dict {<node_instance_name>: NodeInstance, }"""
        nodes_instances = {}

        self._retrieveAndSetRun()

        nodes_instances_runtime_parameters = \
            DomExtractor.extract_nodes_instances_runtime_parameters(self.run_dom, cloud_service_name)

        nodes_runtime_parameters = DomExtractor.extract_nodes_runtime_parameters(self.run_dom)

        for node_instance_name, node_instance_runtime_parameters in nodes_instances_runtime_parameters.items():

            node_instance = NodeInstance(node_instance_runtime_parameters)
            node_name = node_instance.get_node_name()

            if nodes_runtime_parameters:
                node_runtime_parameters = nodes_runtime_parameters.get(node_name, {})
                if node_runtime_parameters:
                    node_instance.set_parameter(NodeDecorator.MAX_PROVISIONING_FAILURES_KEY,
                        node_runtime_parameters.get(NodeDecorator.MAX_PROVISIONING_FAILURES_KEY, '0'))

            image_attributes = DomExtractor.extract_node_image_attributes(self.run_dom, node_name)
            node_instance.set_image_attributes(image_attributes)

            image_targets = DomExtractor.extract_node_image_targets(self.run_dom, node_name)
            node_instance.set_image_targets(image_targets)

            build_state = DomExtractor.extract_node_image_build_state(self.run_dom, node_name)
            node_instance.set_build_state(build_state)

            nodes_instances[node_instance_name] = node_instance

        return nodes_instances

    def _get_nodename(self):
        """Node name derived from the node instance name."""
        return self.node_instance_name.split(
            NodeDecorator.NODE_MULTIPLICITY_SEPARATOR)[0]

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
            self.run_dom = etree.fromstring(run.encode('utf-8'))

    def _retrieve(self, url):
        return self._httpGet(url, 'application/xml')

    def execute(self, resourceUri):
        url = self.runEndpoint
        return self._httpPost(url, resourceUri, 'text/plain')

    def complete_state(self, node_instance_name):
        url = '%s/%s:%s' % (self.run_url, node_instance_name,
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
        if self.ignoreAbort or ignoreAbort:
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

    def unset_runtime_parameter(self, key, ignore_abort=False):
        url = '%s/%s' % (self.run_url, key)

        if (self.ignoreAbort or ignore_abort):
            url += SlipStreamHttpClient.URL_IGNORE_ABORT_ATTRIBUTE_QUERY

        self._httpDelete(url)

    def _httpGet(self, url, accept='application/xml'):
        return self.get(url, accept, retry=self.retry)

    def _httpPut(self, url, body=None, contentType='application/xml', accept='application/xml'):
        return self.put(url, body, contentType, accept, retry=self.retry)

    def _httpPost(self, url, body=None, contentType='application/xml'):
        return self.post(url, body, contentType, retry=self.retry)

    def _httpDelete(self, url, body=None):
        return self.delete(url, body=body, retry=self.retry)

    def get(self, url, accept='application/xml', retry=True):
        resp = self._call(url, 'GET', accept=accept, retry=retry)
        return resp, resp.text

    def put(self, url, body=None, contentType='application/xml',
            accept='application/xml', retry=True):
        resp = self._call(url, 'PUT', body, contentType, accept, retry=retry)
        return resp, resp.text

    def post(self, url, body=None, contentType='application/xml', retry=True):
        resp = self._call(url, 'POST', body, contentType, retry=retry)
        return resp, resp.text

    def delete(self, url, body=None, retry=True):
        resp = self._call(url, 'DELETE', body, retry=retry)
        return resp, resp.text

    def _call(self, url, method,
              body=None,
              contentType='application/xml',
              accept='application/xml',
              retry=True):

        def _handle3xx(resp):
            raise Exception("Redirect should have been handled by HTTP library."
                            "%s: %s" % (resp.status_code, resp.reason))

        def _handle4xx(resp):
            if resp.status_code == CONFLICT_ERROR:
                raise Exceptions.AbortException(_extract_detail(resp.text))
            if resp.status_code == PRECONDITION_FAILED_ERROR:
                raise Exceptions.NotYetSetException(_extract_detail(resp.text))
            if resp.status_code == EXPECTATION_FAILED_ERROR:
                raise Exceptions.TerminalStateException(_extract_detail(
                    resp.text))
            if resp.status_code == TOO_MANY_REQUESTS_ERROR:
                raise Exceptions.TooManyRequestsError("Too Many Requests")

            if resp.status_code == NOT_FOUND_ERROR:
                clientEx = Exceptions.NotFoundError(resp.reason)
            else:
                detail = _extract_detail(resp.text)
                detail = detail and detail or (
                    "%s (%d)" % (resp.reason, resp.status_code))
                msg = "Failed calling method %s on url %s, with reason: %s" % (
                    method, url, detail)
                clientEx = Exceptions.ClientError(msg)

            clientEx.code = resp.status_code
            raise clientEx

        def _handle5xx(resp):
            if resp.status_code == SERVICE_UNAVAILABLE_ERROR:
                raise Exceptions.ServiceUnavailableError(
                    "SlipStream is in maintenance.")
            else:
                raise Exceptions.ServerError(
                    "Failed calling method %s on url %s, with reason: %d: %s"
                    % (method, url, resp.status_code, resp.reason))

        def _extract_detail(content):
            if not content:
                return content
            try:
                return etree.fromstring(content).text
            except Exception:
                return content

        def _build_headers():
            headers = {}
            if contentType:
                headers['Content-Type'] = contentType
            if accept:
                headers['Accept'] = accept

            return headers

        def _request(headers):
            try:
                return self.session.request(method, url,
                                            data=body,
                                            headers=headers,
                                            verify=self.host_cert_verify)
            except requests.exceptions.InvalidSchema as ex:
                raise Exceptions.ClientError("Malformed URL: %s" % ex)
            except httplib.BadStatusLine:
                raise Exceptions.NetworkError(
                    "Error: BadStatusLine contacting: %s" % url)

        def _handle_response(resp):
            self._log_response(resp)

            if 100 <= resp.status_code < 300:
                return resp

            if 300 <= resp.status_code < 400:
                return _handle3xx(resp)

            if 400 <= resp.status_code < 500:
                return _handle4xx(resp)

            if 500 <= resp.status_code < 600:
                return _handle5xx(resp)

            raise Exceptions.NetworkError('Unknown HTTP return code: %s' %
                                          resp.status_code)

        self.init_session(url)

        self._log_normal(
            'Contacting the server with %s, at: %s' % (method, url))

        retry_until = 60 * 60 * 24 * 7  # 7 days in seconds
        max_wait_time = 60 * 15  # 15 minutes in seconds
        retry_count = 0

        first_request_time = time.time()

        while True:
            try:
                headers = _build_headers()
                resp = _request(headers)
                resp = _handle_response(resp)
                with self.lock:
                    if self.too_many_requests_count > 0:
                        self.too_many_requests_count -= 1
                return resp

            except (Exceptions.TooManyRequestsError,
                    Exceptions.ServiceUnavailableError) as ex:
                sleep = min(
                    abs(float(self.too_many_requests_count) / 10.0 * 290 + 10),
                    300)

            except (httplib.HTTPException, socket.error, HTTPError, RequestException,
                    Exceptions.NetworkError, Exceptions.ServerError) as ex:
                timed_out = (time.time() - first_request_time) >= retry_until
                if retry is False or timed_out:
                    self._log_normal('HTTP call error: %s' % ex)
                    raise
                sleep = min(float(retry_count) * 10.0, float(max_wait_time))
                retry_count += 1

            sleep += (random() * sleep * 0.2) - (sleep * 0.1)
            with self.lock:
                if self.too_many_requests_count < 11:
                    self.too_many_requests_count += 1
            self._log_normal('Error: %s. Retrying in %s seconds.' % (ex, sleep))
            time.sleep(sleep)
            self._log_normal('Retrying...')

    def _get_login_creds(self):
        if hasattr(self, 'username') and hasattr(self, 'password'):
            return {'username': self.username, 'password': self.password}
        elif hasattr(self, 'api_key') and hasattr(self, 'api_secret'):
            return {'key': self.api_key, 'secret': self.api_secret}
        else:
            return {}

    def init_session(self, url):
        if self.session is None:
            url_parts = urlparse(url)
            endpoint = '%s://%s' % url_parts[:2]
            login_creds = self._get_login_creds()
            if not login_creds:
                self._log_normal('WARNING: No login credentials provided. '
                                 'Assuming cookies from a persisted cookie-jar %s will be used.'
                                 % self.cookie_filename)
            api = Api(endpoint=endpoint, cookie_file=self.cookie_filename,
                      reauthenticate=True, login_creds=login_creds)
            self.session = api.session

    def _log_normal(self, message):
        util.printDetail(message, self.verboseLevel,
                         util.VERBOSE_LEVEL_NORMAL)

    def _log_debug(self, message):
        util.printDetail(message, self.verboseLevel,
                         util.VERBOSE_LEVEL_DETAILED)

    def _log_response(self, resp, max_characters=1000):
        msg = 'Received response: %s\nWith content: %s' % (resp, resp.text)
        if len(msg) > max_characters:
            msg = '%s\n                         %s' % (
                msg[:max_characters], '::::: Content truncated :::::')
        self._log_debug(msg)

    def _printDetail(self, message):
        util.printDetail(message, self.verboseLevel, util.VERBOSE_LEVEL_DETAILED)

    def put_new_image_id(self, image_resource_uri, image_id):
        url = self.serviceurl + '/' + image_resource_uri
        self._printDetail('Set new image id: %s %s' % (url, image_id))
        self._httpPut(url, image_id)

    def launchDeployment(self, params):
        body = '&'.join(params)
        resp, _ = self._httpPost(self.runEndpoint, body,
                                 contentType='text/plain')
        return resp.headers['location']

    def getRunState(self, uuid=None, ignoreAbort=True):
        if not uuid and not self.diid:
            raise Exceptions.ExecutionException("Run ID should be provided "
                                                "to get state.")
        state_key = NodeDecorator.globalNamespacePrefix + NodeDecorator.STATE_KEY
        self.run_url = self.runEndpoint + '/' + (uuid or self.diid)
        return self.getRuntimeParameter(state_key, ignoreAbort=ignoreAbort)

    def remove_instances_from_run(self, node_name, ids, detele_ids_only=True):
        """ids : []"""
        url = '%s/%s' % (self.run_url, node_name)
        body = "ids=%s" % ','.join(map(str, ids))
        if detele_ids_only:
            body = body + '&delete-ids-only=true'
        self._httpDelete(url, body=body)

    def get_server_configuration(self):
        _, config = self._retrieve(self.configuration_endpoint)
        return config

    def login(self, username, password):
        self.api.login_internal(username=username, password=password)

    def logout(self):
        self.api.logout()

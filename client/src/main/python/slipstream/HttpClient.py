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

import os
import time
import base64
import httplib
import httplib2
import socket

from random import random
from threading import Lock

import slipstream.exceptions.Exceptions as Exceptions
import slipstream.util as util

etree = util.importETree()


class HttpClient(object):

    def __init__(self, username=None, password=None, cookie=None,
                 configHolder=None):
        self.cookie = cookie
        self.username = username
        self.password = password
        self.verboseLevel = util.VERBOSE_LEVEL_NORMAL
        self.cookieFilename = os.path.join(os.path.expanduser('~'), '.slipstream-cookie')
        self.disableSslCertificateValidation = True

        self.lock = Lock()
        self.too_many_requests_count = 0

        if configHolder:
            configHolder.assign(self)

        self.httpObject = self._getHttpObject()

    def get(self, url, accept='application/xml', retry=True):
        return self._call(url, 'GET', accept=accept, retry=retry)

    def put(self, url, body=None, contentType='application/xml', accept='application/xml', retry=True):
        return self._call(url, 'PUT', body, contentType, accept, retry=retry)

    def post(self, url, body=None, contentType='application/xml', accept='application/xml', retry=True):
        return self._call(url, 'POST', body, contentType, retry=retry)

    def delete(self, url, body=None, retry=True):
        return self._call(url, 'DELETE', body, retry=retry)

    def _call(self, url, method,
              body=None,
              contentType='application/xml',
              accept='application/xml',
              headers={},
              retry=True):

        def _convertContent(content):
            try:
                content = unicode(content, 'utf-8')
            except:
                # If it fails (e.g. it's not a string-like media-type) ignore it
                pass
            return content

        def _handle2xx(resp):
            if not self.cookie:
                self.cookie = resp.get('set-cookie', None)
                if self.cookie:
                    self._saveCookie()
            return resp, content

        def _handle3xx(resp):
            if resp.status == 302:
                # Redirected
                resp, content = self._call(resp['location'], method, body, accept)
            else:
                raise Exception(
                    "Should have been handled by httplib2!! %s: %s" % (resp.status,
                                                                       resp.reason))
            return resp, content

        def _handle4xx(resp):
            CONFLICT_ERROR = 409
            PRECONDITION_FAILED_ERROR = 412
            EXPECTATION_FAILED_ERROR = 417
            TOO_MANY_REQUESTS_ERROR = 429

            if resp.status == CONFLICT_ERROR:
                raise Exceptions.AbortException(_extractDetail(content))
            if resp.status == PRECONDITION_FAILED_ERROR:
                raise Exceptions.NotYetSetException(_extractDetail(content))
            if resp.status == EXPECTATION_FAILED_ERROR:
                raise Exceptions.TerminalStateException(_extractDetail(content))
            if resp.status == TOO_MANY_REQUESTS_ERROR:
                raise Exceptions.TooManyRequestsError("Too Many Requests")

            # FIXME: fix the server such that 406 is not returned when cookie expires
            if resp.status == 401 or resp.status == 406:
                self._createAuthenticationHeader()

            if resp.status == 404:
                clientEx = Exceptions.NotFoundError(resp.reason)
            else:
                detail = _extractDetail(content)
                detail = detail and detail or ("%s (%d)" % (resp.reason, resp.status))
                msg = "Failed calling method %s on url %s, with reason: %s" % (
                    method, url, detail)
                clientEx = Exceptions.ClientError(msg)

            clientEx.code = resp.status
            raise clientEx

        def _handle5xx(resp):
            SERVICE_UNAVAILABLE_ERROR = 503

            if resp.status == SERVICE_UNAVAILABLE_ERROR:
                raise Exceptions.ServiceUnavailableError("SlipStream is in maintenance.")
            else:
                raise Exceptions.ServerError("Failed calling method %s on url %s, with reason: %d: %s"
                                             % (method, url, resp.status, resp.reason))

        def _extractDetail(xmlContent):
            if xmlContent == '':
                return xmlContent

            try:
                # This is an XML
                errorMsg = etree.fromstring(xmlContent).text
            except Exception:
                # ... or maybe not.
                errorMsg = xmlContent

            return errorMsg

        def _buildHeaders():
            headers = {}
            if contentType:
                headers['Content-Type'] = contentType
            if accept:
                headers['Accept'] = accept

            headers.update(self._createAuthenticationHeader())

            return headers

        def _request(headers):
            try:
                if len(headers):
                    resp, content = h.request(url, method, body, headers=headers)
                else:
                    resp, content = h.request(url, method, body)
            except httplib.BadStatusLine:
                raise Exceptions.NetworkError(
                    "Error: BadStatusLine contacting: %s" % url)
            except httplib2.RelativeURIError as ex:
                raise Exceptions.ClientError('%s' % ex)

            return resp, content

        def _handleResponse(resp, content):
            self._printDetail('Received response: %s\n                         '
                              'With content: %s'
                              % (resp, _convertContent(content)))

            if str(resp.status).startswith('2'):
                return _handle2xx(resp)

            if str(resp.status).startswith('3'):
                return _handle3xx(resp)

            if str(resp.status).startswith('4'):
                return _handle4xx(resp)

            if str(resp.status).startswith('5'):
                return _handle5xx(resp)

            raise Exceptions.NetworkError('Unknown return code: %s' % resp.status)

        self._printDetail('Contacting the server with %s, at: %s' % (method, url))

        retry_until = 60 * 60 * 24 * 7 # 7 days in seconds
        max_wait_time = 60 * 15 # 15 minutes in seconds
        retry_count = 0

        first_request_time = time.time()

        h = self.httpObject
        while True:
            try:
                resp, content = _request(_buildHeaders())
                resp, content = _handleResponse(resp, content)
                with self.lock:
                    if self.too_many_requests_count > 0:
                        self.too_many_requests_count -= 1
                return resp, content

            except (Exceptions.TooManyRequestsError, Exceptions.ServiceUnavailableError) as ex:
                sleep = min(abs(float(self.too_many_requests_count) / 10.0 * 290 + 10), 300)
                sleep += (random() * sleep * 0.2) - (sleep * 0.1)
                with self.lock:
                    if self.too_many_requests_count < 11:
                        self.too_many_requests_count += 1
                util.printDetail('Error: %s. Retrying in %s seconds.' % (ex, sleep))
                time.sleep(sleep)
                util.printDetail('Retrying...')

            except (httplib.HTTPException, httplib2.HttpLib2Error, socket.error,
                    Exceptions.NetworkError, Exceptions.ServerError) as ex:
                if retry == False or (time.time() - first_request_time) >= retry_until:
                    util.printDetail('HTTP call error: %s' % ex)
                    raise

                sleep = min(float(retry_count) * 10.0, float(max_wait_time))
                sleep += (random() * sleep * 0.2) - (sleep * 0.1)
                retry_count += 1

                util.printDetail('Error: %s. Retrying in %s seconds.' % (ex, sleep))
                time.sleep(sleep)
                util.printDetail('Retrying...')

    def _getHttpObject(self):
        h = httplib2.Http(cache=util.HTTP_CACHEDIR, timeout=300,
                          disable_ssl_certificate_validation=self.disableSslCertificateValidation)
        h.force_exception_to_status_code = False
        return h

    def _createAuthenticationHeader(self):
        """ Authenticate with the server.  Use the username/password passed as
            input parameters, otherwise use the ones provided by the instance
            cloud context. """

        useBasicAuthentication = not self.cookie and (self.username and self.password)
        if useBasicAuthentication:
            auth = base64.encodestring(self.username + ':' + self.password)
            self._printDetail('Using basic authentication')
            return {'Authorization': 'Basic ' + auth}
        useCookieAuthentication = self.cookie or self._loadCookie()
        if useCookieAuthentication:
            return self._addCookieHeader()

        self._printDetail('Trying without authentication')
        return {}

    def _addCookieHeader(self):
        self._printDetail('Using cookie authentication')
        return {'cookie': self.cookie}

    def _loadCookie(self):
        try:
            self.cookie = open(self.cookieFilename).read()
        except (IOError, OSError):
            pass
        return self.cookie

    def _deleteCookie(self):
        try:
            os.unlink(self.cookieFilename)
        except OSError:
            pass

    def _saveCookie(self):
        try:
            os.makedirs(os.path.dirname(self.cookieFilename))
        except OSError:
            pass
        with open(self.cookieFilename, 'w') as fh:
            fh.write(self.cookie)

    def _printDetail(self, message, max_characters=1000):
        if len(message) > max_characters:
            message = '%s\n                         %s' \
                      % (message[:max_characters], '::::: Content truncated :::::')

        util.printDetail(message, self.verboseLevel, util.VERBOSE_LEVEL_DETAILED)

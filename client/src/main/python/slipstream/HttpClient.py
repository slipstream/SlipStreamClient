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
        self.cookieFilename = os.path.join(util.TMPDIR, 'cookie')
        self.disableSslCertificateValidation = True

        if configHolder:
            configHolder.assign(self)

        self.httpObject = self._getHttpObject()

    def get(self, url, accept='application/xml', retry_number=None):
        return self._call(url, 'GET', accept=accept, retry_number=retry_number)

    def put(self, url, body=None, contentType='application/xml', accept='application/xml', retry_number=None):
        return self._call(url, 'PUT', body, contentType, accept, retry_number=retry_number)

    def post(self, url, body=None, contentType='application/xml', accept='application/xml', retry_number=None):
        return self._call(url, 'POST', body, contentType, retry_number=retry_number)

    def delete(self, url ,retry_number=None):
        return self._call(url, 'DELETE', retry_number=retry_number)

    def _call(self, url, method,
              body=None,
              contentType='application/xml',
              accept='application/xml',
              headers={},
              retry_number=None):

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
            if resp.status == CONFLICT_ERROR:
                raise Exceptions.AbortException(_extractDetail(content))
            if resp.status == PRECONDITION_FAILED_ERROR:
                raise Exceptions.NotYetSetException(_extractDetail(content))
            if resp.status == EXPECTATION_FAILED_ERROR:
                raise Exceptions.TerminalStateException(_extractDetail(content))
            # FIXME: fix the server such that 406 is not returned when cookie expires
            if resp.status == 401 or resp.status == 406:
                headers = self._createAuthenticationHeader()

            msg = "Failed calling method %s on url %s, with reason: %d: %s" % (
                method, url, resp.status, resp.reason)
            if resp.status == 404:
                clientEx = Exceptions.NotFoundError(resp.reason)
            else:
                clientEx = Exceptions.ClientError(msg)
            clientEx.code = resp.status
            raise clientEx

        def _handle5xx(resp):
            raise Exceptions.ServerError(
                "Failed calling method %s on url %s, with reason: %d: %s" % (
                    method, url, resp.status, resp.reason))

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
            self._printDetail('Received response: %s\nwith content:\n %s' % (
                resp, _convertContent(content)))

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

        if retry_number is None:
            retry_number = 0
        max_retry = retry_number

        h = self.httpObject
        while True:
            try:
                resp, content = _request(_buildHeaders())
                resp, content = _handleResponse(resp, content)
                return resp, content
            except (httplib.HTTPException, httplib2.HttpLib2Error, socket.error,
                    Exceptions.NetworkError, Exceptions.ServerError) as ex:
                if retry_number == 0 or max_retry == 0:
                    util.printDetail('HTTP call error: %s' % ex)
                    raise
                else:
                    # Sleep between 10 seconds and 1 minute 30 seconds
                    if max_retry > 0:
                        sleep = retry_number
                    else:
                        sleep = abs(max_retry) - abs(retry_number + abs(max_retry))
                    sleep = min((abs(max_retry) - float(sleep)) / (abs(max_retry)-1) * 80 + 10, 90)

                    retry_number = retry_number - 1
                    util.printDetail('HTTP call error: %s \n%s of %s attempts remaining. \nRetrying in %s seconds' % (ex, retry_number, max_retry, sleep))
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

    def _printDetail(self, message):
        util.printDetail(message, self.verboseLevel, util.VERBOSE_LEVEL_DETAILED)

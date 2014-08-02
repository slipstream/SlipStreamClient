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

import sys
import time
import subprocess

from SlipStreamHttpClient import SlipStreamHttpClient

from exceptions.Exceptions import NotYetSetException
from exceptions.Exceptions import TimeoutException
from exceptions.Exceptions import ClientError

from NodeDecorator import NodeDecorator
import slipstream.util as util


class Client(object):
    TMPDIR = util.TMPDIR
    REPORTSDIR = util.REPORTSDIR
    WINDOWS_REPORTSDIR = util.WINDOWS_REPORTSDIR
    IMAGE = NodeDecorator.IMAGE
    DEPLOYMENT = NodeDecorator.DEPLOYMENT

    def __init__(self, configHolder):
        self.noBlock = True
        self.ignoreAbort = False
        self.timeout = 30
        self.verboseLevel = 1
        self.verboseThreshold = 1
        configHolder.assignConfigAndOptions(self)
        self.context = configHolder.context
        self.httpClient = SlipStreamHttpClient(configHolder)

    def _loadModule(self, moduleName):
        return util.loadModule(moduleName)

    def getRuntimeParameter(self, key):

        _key = self._qualifyKey(key)

        if self.noBlock:
            value = self._getRuntimeParameter(_key, self.ignoreAbort)
        else:
            value = None
            timer = 0
            while True:
                try:
                    value = self._getRuntimeParameter(_key, self.ignoreAbort)
                except NotYetSetException:
                    pass
                if value is not None:
                    break
                if self.timeout != 0 and timer >= self.timeout:
                    raise TimeoutException(
                        "Exceeded timeout limit of %s waiting for key '%s' "
                        "to be set" % (self.timeout, _key))
                print >> sys.stderr, "Waiting for %s" % _key
                sys.stdout.flush()
                sleepTime = 5
                time.sleep(sleepTime)
                timer += sleepTime
        return value

    def launchDeployment(self, params):
        """
        @return: Run location
        @rtype: {str}
        """
        return self.httpClient.launchDeployment(params)

    def getRunState(self, uuid, ignoreAbort=True):
        return self.httpClient.getRunState(uuid, ignoreAbort=ignoreAbort)

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

    def setNodeName(self, value):
        self.context['nodename'] = value

    def _getNodeName(self):
        return self.context['nodename']

    def _getRuntimeParameter(self, key, ignoreAbort=False):
        specialKeys = ['nodename']
        if key in specialKeys:
            return self.context['key']

        content = self.httpClient.getRuntimeParameter(key)

        return content

    def setRuntimeParameter(self, key, value):
        _key = self._qualifyKey(key)
        self.httpClient.setRuntimeParameter(_key, util.removeASCIIEscape(value))

    def reset(self):
        self.httpClient.reset()

    def executScript(self, script):
        return self._systemCall(script, retry=False)

    def _systemCall(self, cmd, retry=True):
        """
        Execute system call and return stdout.
        Raise an exception if the command fails
        """
        self._printStep('Executing command: %s' % cmd)
        p = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, close_fds=True)
        (child_stdin, child_stdout) = (p.stdin, p.stdout)
        child_stdin = child_stdin
        stdout = []
        while True:
            out = child_stdout.readlines(1)
            if not out:
                break
            stdout.extend(out)
            sys.stdout.writelines(out)
        returnCode = p.wait()
        if returnCode:
            if retry:
                return self._systemCall(cmd, False)
            else:
                raise ClientError("Error executing command '%s', with error "
                                  "code: %s" % (cmd, returnCode))
        return stdout

    def _printStep(self, message):
        util.printStep(message)

    def _printDetail(self, message):
        util.printDetail(message, self.verboseLevel, self.verboseThreshold)

    def getCategory(self):
        return self.httpClient.get_run_category()

    def fail(self, message):
        abort = self._qualifyKey(NodeDecorator.ABORT_KEY)
        self.httpClient.setRuntimeParameter(abort, message)

    def complete_state(self):
        nodeName = self._getNodeName()
        self.httpClient.complete_state(nodeName)

    def terminateRun(self):
        self.httpClient._httpDelete(self.httpClient.run_url)

    def getGlobalAbortMessage(self):
        return self.httpClient.getGlobalAbortMessage()

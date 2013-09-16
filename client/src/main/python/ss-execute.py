#!/usr/bin/env python
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
import os
from optparse import OptionParser

from slipstream.CommandBase import CommandBase
from slipstream.HttpClient import HttpClient   
from slipstream.ConfigHolder import ConfigHolder
import slipstream.util as util


class MainProgram(CommandBase):
    '''A command-line program to execute a run of creating a new machine.'''
    
    REF_QNAME = 'refqname'

    def __init__(self, argv=None):
        self.moduleUri = None
        self.username = None
        self.password = None
        self.cookie = None
        self.endpoint = None
        self.parameters = {}
        super(MainProgram, self).__init__(argv)

    def parse(self):
        usage = '''usage: %prog [options] <module-url>

<module-uri>    Full URL to the module to execute. For example Public/Tutorials/HelloWorld/client_server'''

        self.parser.usage = usage
        
        self.parser.add_option('-u','--username', dest='username',
                               help='SlipStream username', metavar='USERNAME',
                               default=os.environ.get('SLIPSTREAM_USERNAME'))
        self.parser.add_option('-p','--password', dest='password',
                               help='SlipStream password', metavar='PASSWORD',
                               default=os.environ.get('SLIPSTREAM_PASSWORD'))

        self.parser.add_option('--cookie', dest='cookieFilename',
                               help='SlipStream cookie', metavar='FILE',
                               default=os.environ.get('SLIPSTREAM_COOKIEFILE', 
                                                      os.path.join(util.TMPDIR, 'cookie')))

        self.parser.add_option('--endpoint', dest='endpoint',
                               help='SlipStream server endpoint', metavar='URL',
                               default=os.environ.get('SLIPSTREAM_ENDPOINT', 'http://slipstream.sixsq.com'))

        self.parser.add_option('--parameters', dest='parameters',
                               help='Deployment or image parameters override. The key must be in a form:'\
                               ' <node-name>:<parameter-name>. Several pairs can be provided comma separated.',
                               metavar="KEY1=VALUE1,KEY2=VALUE2",
                               default='')

        self.options, self.args = self.parser.parse_args()

        self._checkArgs()

        self.resourceUrl = self.args[0]

    def _checkArgs(self):
        if len(self.args) < 1:
            self.parser.error('Missing resource-uri')
        if len(self.args) > 1:
            self.usageExitTooManyArguments()
        self.parameters = self._parseParameters()

    def _parseParameters(self):
        parameters = {}
        if not self.options.parameters:
            return parameters
        for pair in self.options.parameters.split(','):
            parts = pair.split('=')
            if len(parts) != 2:
                self.parser.error('Invalid parameter key/value pair: ' + pair)
            key, value = map(lambda x: x.strip(), parts)
            parameters[key]=value
        return parameters

    def doWork(self):
        configHolder = ConfigHolder(self.options, context={'empty':None}, config={'empty':None})
        client = HttpClient(self.options.username, self.options.password, configHolder=configHolder)

        url = self.options.endpoint + util.RUN_URL_PATH

        data = self._assembleData()

        resp, _ = client.post(url, '&'.join(data), contentType='text/plain', accept='text/plain')
        print resp['location']

    def _assembleData(self):
        self.parameters[self.REF_QNAME] = 'module/' + self.resourceUrl
        return [self._decorateKey(k) + '=' + v for k,v in self.parameters.items()]
        
    def _decorateKey(self, key):
        if key == self.REF_QNAME:
            return key
        parts = key.split(':')
        if len(parts) != 2:
            self.parser.error('Invalid key format: ' + key)
        nodename, key = parts
        return 'parameter--node--' + nodename + '--' + key

if __name__ == "__main__":
    try:
        MainProgram()
    except KeyboardInterrupt:
        print '\n\nExecution interrupted by the user... goodbye!'
        sys.exit(-1)

#!/usr/bin/env python
"""
 SlipStream Client
 =====
 Copyright (C) 2014 SixSq Sarl (sixsq.com)
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
import sys
import xml.etree.ElementTree as ET

from slipstream.command.CommandBase import CommandBase
from slipstream.HttpClient import HttpClient
import slipstream.util as util

class MainProgram(CommandBase):
    '''Recursively download SlipStream modules as XML from server.'''

    def __init__(self, argv=None):
        self.module = ''
        self.username = None
        self.password = None
        self.cookie = None
        self.endpoint = None
        self.purgImageIds = False
        super(MainProgram, self).__init__(argv)

    def parse(self):
        usage = '''usage: %prog [options] <module-url>

<module-uri>    Name of the root module.'''

        self.parser.usage = usage

        self.add_authentication_options()
        self.addEndpointOption()        

        self.parser.add_option('--purge-image-ids', dest='purgImageIds',
                               help='Remove cloud image ids before saving',
                               default=False, action='store_true')

        self.options, self.args = self.parser.parse_args()

        self._checkArgs()

    def _checkArgs(self):
        if len(self.args) == 1:
            self.module = self.args[0]
        if len(self.args) > 1:
            self.usageExitTooManyArguments()

    def _removeRuns(self, root):
        """Remove the run elements from the given document.
           The runs are dynamic and cannot be pushed back
           into the server.  This modified the given XML
           document!"""
        runs = root.find('runs')
        if runs is not None:
            for run in runs.findall('*'):
                runs.remove(run)

    def _removeCloudImageIdentifiers(self, root):
        """Remove the cloudImageIdentifiers element from
           the given document.  These identifiers are not
           portable between SlipStream deployments."""

        ids = root.find('cloudImageIdentifiers')
        if ids is not None:
            for id in ids.findall('*'):
                ids.remove(id)

    def _retrieveModuleAsXml(self, client, module):
        uri = util.MODULE_RESOURCE_PATH
        uri += '/' + module

        url = self.options.endpoint + uri

        _, xml = client.get(url)

        return ET.fromstring(xml)

    def _writeModuleAsXml(self, root_element, module):
        ET.ElementTree(root_element).write('%s.xml' % module.replace('/', '_'))

    def _getModuleChildren(self, module, root_element):
        children = []
        for child in root_element.findall('children/item'):
            module_name = child.attrib['name']
            module_path = '%s/%s' % (module, module_name)
            children.append(module_path)
        return children

    def doWork(self):
        client = HttpClient(self.options.username, self.options.password)
        client.verboseLevel = self.verboseLevel

        queue = [self.module]

        while len(queue) > 0:
            module = queue.pop(0)
            print('Processing: %s' % module)

            root = self._retrieveModuleAsXml(client, module)
            self._removeRuns(root)
            if self.purgImageIds:
                self._removeCloudImageIdentifiers(root)
            self._writeModuleAsXml(root, module)

            for child in self._getModuleChildren(module, root):
                queue.append(child)

if __name__ == "__main__":
    try:
        MainProgram()
    except KeyboardInterrupt:
        print('\n\nExecution interrupted by the user... goodbye!')
        sys.exit(-1)

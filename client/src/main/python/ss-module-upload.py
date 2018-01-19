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

from slipstream.command.CommandBase import CommandBase
from slipstream.HttpClient import HttpClient
import slipstream.util as util
import slipstream.SlipStreamHttpClient as SlipStreamHttpClient

etree = util.importETree()

class MainProgram(CommandBase):
    '''Uploads a collection of modules (in XML format) to the server.'''

    def __init__(self, argv=None):
        self.module = ''
        self.endpoint = None
        self.force = False
        super(MainProgram, self).__init__(argv)

    def parse(self):
        usage = '''usage: %prog [options] <file> ...'''

        self.parser.usage = usage
        self.addEndpointOption()        

        self.parser.add_option('-f', '--force', dest='force',
                               help='Force execution, ignoring errors',
                               default=False, action='store_true')

        self.options, self.args = self.parser.parse_args()

        self._checkArgs()

    def _checkArgs(self):
        if len(self.args) == 0:
            self.usageExit("You must provide at least one file to upload.")
        self.force = self.options.force

    def _check_file(self, file):
        if not os.path.exists(file):
            self.usageExit("Unknown filename: " + file)
        if not os.path.isfile(file):
            self.usageExit("Input is not a file: " + file)

    def _read_module_as_xml(self, contents):
        try:
            return etree.fromstring(contents)
        except Exception as ex:
            print(str(ex))
            if self.verboseLevel:
                raise
            sys.exit(-1)

    def _put(self, url, file, client):
        with open(file) as f:
            try:
                client.put(url, f.read())
            except:
                if self.force is not True:
                    raise

    def doWork(self):
        client = HttpClient()
        client.verboseLevel = self.verboseLevel

        # read all files once to determine the upload URL for each file
        # the URL is used to sort the files into an order that puts
        # parents before children
        projects = {}
        images = {}
        deployments = {}
        for file in self.args:

            self._check_file(file)

            with open(file) as f:
                contents = f.read()

                dom = self._read_module_as_xml(contents)
                attrs = SlipStreamHttpClient.DomExtractor.get_attributes(dom)

                root_node_name = dom.tag
                if root_node_name == 'list':
                    sys.stderr.write('Cannot update root project\n')
                    sys.exit(-1)
                if not dom.tag in ('imageModule', 'projectModule',
                                   'deploymentModule'):
                    sys.stderr.write('Invalid xml\n')
                    sys.exit(-1)

                parts = [attrs['parentUri'], attrs['shortName']]
                uri = '/' + '/'.join([part.strip('/') for part in parts])

                url = self.options.endpoint + uri

                if dom.tag == 'projectModule':
                    projects[url] = file
                elif dom.tag == 'imageModule':
                    images[url] = file
                elif dom.tag == 'deploymentModule':
                    deployments[url] = file

        # now actually do the uploads in the correct order
        # projects must be done first to get the structure, then
        # images, and finally the deployments
        for url in sorted(projects):
            file = projects[url]
            print('Uploading project: %s' % file)
            self._put(url, file, client)

        for url in sorted(images):
            file = images[url]
            print('Uploading image: %s' % file)
            self._put(url, file, client)

        for url in sorted(deployments):
            file = deployments[url]
            print('Uploading deployment: %s' % file)
            self._put(url, file, client)

if __name__ == "__main__":
    try:
        MainProgram()
    except KeyboardInterrupt:
        print('\n\nExecution interrupted by the user... goodbye!')
        sys.exit(-1)

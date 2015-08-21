#!/usr/bin/env python
"""
 SlipStream Client
 =====
 Copyright (C) 2015 SixSq Sarl (sixsq.com)
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

import copy
import os
import sys
import xml.etree.ElementTree as etree

from slipstream.command.CommandBase import CommandBase
from slipstream.SlipStreamHttpClient import DomExtractor
from slipstream.Client import Client
from slipstream.ConfigHolder import ConfigHolder
from slipstream.util import SERVER_CONFIG_FILE_EXT
from slipstream.util import SERVER_CONFIGURATION_DEFAULT_CATEGORIES
from slipstream.util import SERVER_CONFIGURATION_BASICS_CATEGORY
from slipstream.util import SERVER_CONFIGURATION_CONNECTOR_CLASSES_KEY


class MainProgram(CommandBase):

    NO_CONNECTOR_CLASS_MAPPING_MSG = '<CONNECTOR IS INACTIVE. CONNECTOR CLASS NOT KNOWN!>'

    def __init__(self, argv=None):
        self._categories = []
        super(MainProgram, self).__init__(argv)

    def parse(self):
        usage = '''usage: %prog [options]

Takes SlipStream configuration as XML and outputs in section-less .ini format.
The configuration can either be provided as file or a server endpoint.
Different sections (categories) of the configuration can be extracted with --categories option.
'''

        self.parser.usage = usage

        self.add_authentication_options()
        self._add_endpoint_option()

        self.parser.add_option('-o', '--output', dest='output', metavar='FILE',
                               help='File to output the configuration. By default,'
                                    'the configuration is printed to stdout.',
                               default=None)
        self.parser.add_option('-i', '--input', dest='input', metavar='FILE',
                               help='File to read the configuration from.',
                               default=None)
        self.parser.add_option('--categories', dest='categories', metavar='CATEGORIES',
                               help='Comma separated list of categories to extract. '
                                    'By default, all categories will be extracted.', default=None)
        self.parser.add_option('--list-categories', dest='list_categories',
                               help='List available categories.', default=False, action='store_true')
        self.parser.add_option('--file-per-category', dest='file_per_category',
                               help='Store each category into a separate file named by the category '
                                    'and extension %s' % SERVER_CONFIG_FILE_EXT, default=False,
                               action='store_true')
        self.parser.add_option('--connectors-only', dest='connectors_only',
                               help='Dump only configuration of connectors.  Only active '
                                    'connectors are processed.', default=False, action='store_true')
        self.parser.add_option('--inactive-connectors', dest='inactive_connectors',
                               help='Dump inactive connectors as well.  By default only active '
                                    'connectors are processed.', default=False, action='store_true')
        self.parser.remove_option('--cookie')

        self.options, _ = self.parser.parse_args()

        self._check_options()

    def _check_options(self):
        if not (self.options.input or self.options.serviceurl) or (self.options.input and self.options.serviceurl):
            self.usageExit('Either -e or -i should be provided.')

        credentials_provided = (self.options.username and self.options.password)
        if self.options.serviceurl and not credentials_provided:
            self.usageExit('Provide credentials with -u and -p when using -e/--endpoint option.')

        if self.options.categories and self.options.connectors_only:
            self.usageExit('Either --categories or --connectors-only can be provided.')

        if self.options.output and self.options.file_per_category:
            self.usageExit('Either -o/--output or --file-per-category can be provided.')

        if self.options.categories:
            self._categories = self.options.categories.split(',')

    def _add_endpoint_option(self):
        default_endpoint = os.environ.get('SLIPSTREAM_ENDPOINT', None)
        self.parser.add_option('-e', '--endpoint', dest='serviceurl', metavar='URL',
                               help='SlipStream server endpoint',
                               default=default_endpoint)

    def _get_config(self):
        config_dom = self._get_config_dom()
        return DomExtractor.server_config_dom_into_dict(config_dom)

    def _get_config_dom(self):
        if self.options.input:
            config = self._get_config_from_file()
        else:
            config = self._get_config_from_server()
        return etree.fromstring(config)

    def _get_config_from_file(self):
        with open(self.options.input) as fp:
            return fp.read()

    def _get_config_from_server(self):
        ch = ConfigHolder(options=self.options, context={'foo': 'bar'},
                          config={'verboseLevel': self.verboseLevel})
        client = Client(ch)
        return client.get_server_configuration()

    def _output_config(self, config):
        if self.options.list_categories:
            self._print_categories(config)
        elif self.options.output:
            self._write_to_file(self._config_generate_for_categories(config), self.options.output)
        elif self.options.file_per_category:
            self._write_to_file_per_category(self._config_generate_for_categories(config))
        else:
            self._print_config(self._config_generate_for_categories(config))

    def _config_update_for_connector(self, config, connector_class, category, params):
        if not connector_class and self.options.inactive_connectors:
            connector_class = self.NO_CONNECTOR_CLASS_MAPPING_MSG
        if connector_class:
            _params = copy.deepcopy(params)
            if self.options.connectors_only or self.options.file_per_category or \
                    self.options.inactive_connectors:
                _params.insert(0,
                               (SERVER_CONFIGURATION_CONNECTOR_CLASSES_KEY,
                                category + ':' + connector_class))
            config[category] = _params
        else:
            self._print_warning("Skipped inactive connector '%s'. Provide --inactive-connectors to process "
                "inactive connectors." % category)

    def _config_generate_for_categories(self, config):
        cloud_connector_classes = self._get_cloud_connector_classes(config)
        config_new= {}
        for category, params in config.iteritems():
            not_in_requested_category_set = self._categories and (category not in self._categories)
            if not_in_requested_category_set:
                continue
            # Insert 'cloud.connector.class' properties into connector configuration.
            connector_configuration = category not in SERVER_CONFIGURATION_DEFAULT_CATEGORIES
            if connector_configuration:
                self._config_update_for_connector(config_new, cloud_connector_classes.get(category), category, params)
                continue
            elif self.options.connectors_only:
                continue
            config_new[category] = copy.deepcopy(params)

        return config_new

    def _print_warning(self, msg):
        print('# WARNING: %s' % msg)

    @staticmethod
    def _get_cloud_connector_classes(config):
        cloud_connector_classes = {}
        for p in config.get(SERVER_CONFIGURATION_BASICS_CATEGORY):
            k, v = p
            if k == SERVER_CONFIGURATION_CONNECTOR_CLASSES_KEY:
                cloud_connector_classes = dict(map(lambda x: x.strip().split(':'), v.split(',')))
        return cloud_connector_classes

    @staticmethod
    def _print_categories(config):
        categories = config.keys()
        categories.sort()
        for c in categories:
            print(c)

    @staticmethod
    def _print_config(config):
        for k, v in config.iteritems():
            print('# [%s]' % k)
            for param in v:
                print('%s = %s' % param)

    @staticmethod
    def _write_to_file(config, fname):
        with open(fname, 'w') as fh:
            for k, v in config.iteritems():
                fh.write('# [%s]\n' % k)
                for param in v:
                    fh.write('%s = %s\n' % param)

    @staticmethod
    def _write_to_file_per_category(config):
        for k, v in config.iteritems():
            with open(k + SERVER_CONFIG_FILE_EXT, 'w') as fh:
                fh.write('# [%s]\n' % k)
                for param in v:
                    fh.write('%s = %s\n' % param)

    def doWork(self):
        self._output_config(self._get_config())


if __name__ == "__main__":
    try:
        MainProgram()
    except KeyboardInterrupt:
        print('\n\nExecution interrupted by the user... goodbye!')
        sys.exit(-1)

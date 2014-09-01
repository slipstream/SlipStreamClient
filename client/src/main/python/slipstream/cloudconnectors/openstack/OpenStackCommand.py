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

from slipstream.command.CloudClientCommand import CloudClientCommand
from slipstream.cloudconnectors.openstack.OpenStackClientCloud import OpenStackClientCloud


class OpenStackCommand(CloudClientCommand):

    def __init__(self):
        self.PROVIDER_NAME = OpenStackClientCloud.cloudName
        super(OpenStackCommand, self).__init__()

    def _setCommonOptions(self):
        self.parser.add_option('--username', dest='key',
                               help='Key',
                               default='', metavar='KEY')

        self.parser.add_option('--password', dest='secret',
                               help='Secret',
                               default='', metavar='SECRET')

        self.parser.add_option('--endpoint', dest='endpoint',
                               help='Identity service (Keystone)',
                               default='', metavar='ENDPOINT')

        self.parser.add_option('--region', dest='region',
                               help='Region (default: regionOne)',
                               default='regionOne', metavar='REGION')
        
        self.parser.add_option('--service-type', dest='service_type',
                               help='Type-name of the service which provides the instances functionality (default: compute)',
                               default='compute', metavar='TYPE')
        
        self.parser.add_option('--service-name', dest='service_name',
                               help='Name of the service which provides the instances functionality (default: nova)',
                               default='nova', metavar='NAME')
        
        self.parser.add_option('--project', dest='project',
                               help='Project (Tenant)',
                               default='', metavar='PROJECT')
        
    def _checkOptions(self):
        if not all((self.options.key, self.options.secret,
                    self.options.endpoint, self.options.region)):
            self.parser.error('Some mandatory options were not given values.')
        self.checkOptions()

    def _setUserInfo(self):
        self.userInfo[self.PROVIDER_NAME + '.username'] = self.options.key
        self.userInfo[self.PROVIDER_NAME + '.password'] = self.options.secret
        self.userInfo[self.PROVIDER_NAME + '.endpoint'] = self.options.endpoint
        self.userInfo[self.PROVIDER_NAME + '.service.type'] = self.options.service_type
        self.userInfo[self.PROVIDER_NAME + '.service.name'] = self.options.service_name
        self.userInfo[self.PROVIDER_NAME + '.service.region'] = self.options.region
        self.userInfo[self.PROVIDER_NAME + '.tenant.name'] = self.options.project



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

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

from slipstream.command.CloudClientCommand import CloudClientCommand
from slipstream.NodeDecorator import KEY_RUN_CATEGORY
from slipstream.ConfigHolder import ConfigHolder


class TerminateInstancesCommand(CloudClientCommand):

    INSTANCE_IDS_KEY = 'instance-ids'

    def __init__(self, timeout=600):
        super(TerminateInstancesCommand, self).__init__(timeout)

    def _set_command_specific_options(self, parser):
        parser.add_option('--' + self.INSTANCE_IDS_KEY, dest=self.INSTANCE_IDS_KEY,
                          help='Instance ID (can be used multiple times)',
                          action='append', default=[], metavar='ID')

    def _get_command_mandatory_options(self):
        return [self.INSTANCE_IDS_KEY]

    def do_work(self):
        ids = self.get_option(self.INSTANCE_IDS_KEY)
        ch = ConfigHolder(options={'verboseLevel': self.options.verbose and 3 or 0,
                                   'http_max_retries': 0,
                                   KEY_RUN_CATEGORY: ''},
                          context={'foo': 'bar'})
        cc = self.get_connector_class()(ch)
        cc._initialization(self.user_info, **self.get_initialization_extra_kwargs())

        if cc.has_capability(cc.CAPABILITY_VAPP):
            cc.stop_vapps_by_ids(ids)
        else:
            cc.stop_vms_by_ids(ids)

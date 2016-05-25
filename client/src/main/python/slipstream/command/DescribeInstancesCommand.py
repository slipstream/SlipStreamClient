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
from slipstream.util import nostdouterr


class DescribeInstancesCommand(CloudClientCommand):

    DEFAULT_TIMEOUT = 30

    def _vm_get_state(self, cc, vm):
        raise NotImplementedError()

    def _sanitize_for_output(self, text):
        if text is None:
            text = ''
        elif not isinstance(text, basestring):
            text = str(text)
        return text.replace(',', '')

    def _vm_get_id(self, cc, vm):
        return self._sanitize_for_output(cc._vm_get_id(vm))

    def _vm_get_ip(self, cc, vm):
        return self._sanitize_for_output(cc._vm_get_ip_from_list_instances(vm))

    def _vm_get_cpu(self, cc, vm):
        return self._sanitize_for_output(cc._vm_get_cpu(vm))

    def _vm_get_ram(self, cc, vm):
        return self._sanitize_for_output(cc._vm_get_ram(vm))

    def _vm_get_root_disk(self, cc, vm):
        return self._sanitize_for_output(cc._vm_get_root_disk(vm))

    def _vm_get_instance_type(self, cc, vm):
        return self._sanitize_for_output(cc._vm_get_instance_type(vm))

    def _list_instances(self, cc):
        return cc.list_instances()

    def __init__(self):
        super(DescribeInstancesCommand, self).__init__()

    def _get_default_timeout(self):
        return self.DEFAULT_TIMEOUT

    def do_work(self):
        with nostdouterr(self.get_option('verbose')):
            cc, vms = self._describe_instances()
        self._print_results(cc, vms)

    def _describe_instances(self):
        ch = ConfigHolder(options={'verboseLevel': 0,
                                   'retry': False,
                                   KEY_RUN_CATEGORY: ''},
                          context={'foo': 'bar'})
        cc = self.get_connector_class()(ch)
        cc._initialization(self.user_info, **self.get_initialization_extra_kwargs())
        vms = self._list_instances(cc)
        return cc, vms

    def _print_results(self, cc, vms):
        print "id, state, ip, cpu [nb], ram [MB], root disk [GB], instance-type [name]"
        for vm in vms:
            print ', '.join([
                self._vm_get_id(cc, vm),
                self._vm_get_state(cc, vm) or 'Unknown',
                self._vm_get_ip(cc, vm),
                self._vm_get_cpu(cc, vm),
                self._vm_get_ram(cc, vm),
                self._vm_get_root_disk(cc, vm),
                self._vm_get_instance_type(cc, vm)])

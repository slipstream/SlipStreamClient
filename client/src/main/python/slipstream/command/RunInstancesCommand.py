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
import sys

from slipstream.command.CloudClientCommand import CloudClientCommand
from slipstream.NodeDecorator import NodeDecorator, KEY_RUN_CATEGORY, RUN_CATEGORY_DEPLOYMENT
from slipstream.NodeInstance import NodeInstance
from slipstream.ConfigHolder import ConfigHolder
from slipstream.util import nostdouterr


saved_stdout = sys.stdout


def publish_vm_info(self, vm, node_instance):
    print >> saved_stdout, '%s,%s' % (self._vm_get_id(vm), self._vm_get_ip(vm))


class RunInstancesCommand(CloudClientCommand):

    IMAGE_ID_KEY        = 'image-id'
    PLATFORM_KEY        = 'platform'
    LOGIN_USER_KEY      = 'login-username'
    LOGIN_PASS_KEY      = 'login-password'
    NETWORK_TYPE        = 'network-type'
    ROOT_DISK_SIZE      = 'disk'
    EXTRA_DISK_VOLATILE = 'extra-disk-volatile'
    DEFAULT_TIMEOUT     = 600

    def get_cloud_specific_node_inst_cloud_params(self):
        return {}

    def get_cloud_specific_node_inst_image_attributes(self):
        return {}

    def get_cloud_specific_node_inst_attributes(self):
        return {}

    def __init__(self):
        super(RunInstancesCommand, self).__init__()

    def _set_command_specific_options(self, parser):
        parser.add_option('--' + self.IMAGE_ID_KEY, dest=self.IMAGE_ID_KEY,
                          help='Image ID', default='', metavar='IMAGEID')

        parser.add_option('--' + self.PLATFORM_KEY, dest=self.PLATFORM_KEY,
                          help='Platform (eg: Ubuntu, CentOS, Windows, ...)',
                          default='linux', metavar='PLATFORM')

        parser.add_option('--' + self.NETWORK_TYPE, dest=self.NETWORK_TYPE,
                          help='Network type (public or private)',
                          default='Public', metavar='NETWORK-TYPE')

        parser.add_option('--' + self.ROOT_DISK_SIZE, dest=self.ROOT_DISK_SIZE,
                          help='Size of the root disk (in GB)',
                          default='', metavar='ROOT-DISK-SIZE')

        parser.add_option('--' + self.EXTRA_DISK_VOLATILE, dest=self.EXTRA_DISK_VOLATILE,
                          help='Size of the volatile extra disk (in GB)',
                          default='', metavar='EXTRA-DISK-VOLATILE')

        parser.add_option('--' + self.LOGIN_USER_KEY, dest=self.LOGIN_USER_KEY,
                          help='Username of the user to use to contextualize the instance',
                          default='', metavar='USER')

        parser.add_option('--' + self.LOGIN_PASS_KEY, dest=self.LOGIN_PASS_KEY,
                          help='Password of the user to use to contextualize the instance',
                          default='', metavar='PASS')

        parser.add_option('--' + NodeDecorator.NATIVE_CONTEXTUALIZATION_KEY, dest=NodeDecorator.NATIVE_CONTEXTUALIZATION_KEY,
                          help='When SlipStream should use the native Cloud contextualization (instead of SSH/WinRM)\nPossible values: never|always|linux-only|windows-only',
                          default='', metavar='NATIVE_CONTEXTUALIZATION')

    def _get_command_mandatory_options(self):
        return [self.IMAGE_ID_KEY,
                self.PLATFORM_KEY,
                self.NETWORK_TYPE]

    def _get_command_specific_user_cloud_params(self):
        native_contextualization = self.get_option(NodeDecorator.NATIVE_CONTEXTUALIZATION_KEY)
        if native_contextualization:
            return {NodeDecorator.NATIVE_CONTEXTUALIZATION_KEY: native_contextualization}
        else:
            return {}

    def _get_default_timeout(self):
        return self.DEFAULT_TIMEOUT

    def _get_node_instance(self):
        runtime_parameters = {
            NodeDecorator.NODE_INSTANCE_NAME_KEY: self.get_node_instance_name(),
            'cloudservice': self._cloud_instance_name,
            'image.platform': self.get_option(self.PLATFORM_KEY),
            'image.imageId': self.get_option(self.IMAGE_ID_KEY),
            'image.id': self.get_option(self.IMAGE_ID_KEY),
            'network': self.get_option(self.NETWORK_TYPE)
        }

        if self.get_option(self.ROOT_DISK_SIZE):
            runtime_parameters.update({'disk.GB':
                                        self.get_option(self.ROOT_DISK_SIZE)})

        if self.get_option(self.EXTRA_DISK_VOLATILE):
            runtime_parameters.update({'extra.disk.volatile':
                                        self.get_option(self.EXTRA_DISK_VOLATILE)})

        if self.get_option(self.LOGIN_USER_KEY):
            runtime_parameters.update({NodeInstance.IMAGE_ATTRIBUTE_PREFIX + '.' + NodeDecorator.LOGIN_USER_KEY:
                                       self.get_option(self.LOGIN_USER_KEY)})

        return NodeInstance(runtime_parameters)

    def _get_command_specific_node_inst_cloud_params(self):
        cloud_params = {}
        if self.get_option(self.LOGIN_PASS_KEY):
            cloud_params[NodeDecorator.LOGIN_PASS_KEY] = self.get_option(self.LOGIN_PASS_KEY)
        return cloud_params

    def do_work(self):
        node_instance = self._get_node_instance()
        node_instance.set_cloud_parameters(self._get_command_specific_node_inst_cloud_params())
        node_instance.set_cloud_parameters(self.get_cloud_specific_node_inst_cloud_params())
        node_instance.set_image_attributes(self.get_cloud_specific_node_inst_image_attributes())
        node_instance.set_attributes(self.get_cloud_specific_node_inst_attributes())

        with nostdouterr(self.get_option('verbose')):
            self._run_instance(node_instance)

    def _run_instance(self, node_instance):
        nodename = node_instance.get_name()

        cloud_connector_class = self.get_connector_class()
        cloud_connector_class._publish_vm_info = publish_vm_info

        verbose_level = self.get_option('verbose') and 3 or 0
        ch = ConfigHolder(options={'verboseLevel': verbose_level,
                                   'retry': False,
                                    KEY_RUN_CATEGORY: RUN_CATEGORY_DEPLOYMENT},
                          context={'foo': 'bar'},
                          config={'foo': 'bar'})

        cc = cloud_connector_class(ch)
        cc.start_nodes_and_clients(self.user_info, {nodename: node_instance},
                                   self.get_initialization_extra_kwargs())

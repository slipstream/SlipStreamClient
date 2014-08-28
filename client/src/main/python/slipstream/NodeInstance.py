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

import slipstream.util as util

from slipstream.NodeDecorator import NodeDecorator


class NodeInstance(object):

    IMAGE_ATTRIBUTE_PREFIX = 'image'

    def __init__(self, runtime_parameters={}):
        self.__parameters = runtime_parameters

    def __str__(self):
        return 'NodeInstance(%s)' % self.__parameters

    def __repr__(self):
        return self.__str__()

    def __get(self, parameter_name, default_value=None):
        parameter = self.__parameters.get(parameter_name, default_value)
        # If the parameter exist but is None, we return the default value
        if parameter is None:
            parameter = default_value
        return parameter

    def __set(self, parameter_name, value):
        self.__parameters[parameter_name] = value

    def get_image_attribute(self, attribute_name, default_value=None):
        return self.__get('%s.%s' %
                          (self.IMAGE_ATTRIBUTE_PREFIX, attribute_name),
                          default_value)

    def set_image_attributes(self, image_attributes):
        for key, value in image_attributes.items():
            self.__set('%s.%s' % (self.IMAGE_ATTRIBUTE_PREFIX, key), value)

    def set_image_targets(self, image_targets):
        for key, value in image_targets.items():
            self.__set('%s.%s' % (self.IMAGE_ATTRIBUTE_PREFIX, key), value)

    def is_orchestrator(self):
        return util.str2bool(self.__get(NodeDecorator.IS_ORCHESTRATOR_KEY,
                                        'False'))

    def is_windows(self):
        return self.get_platform().lower() == 'windows'

    def get_cloud(self):
        return self.__get(NodeDecorator.CLOUDSERVICE_KEY)

    def get_cloud_parameter(self, parameter_name, default_value=None):
        return self.__get('%s.%s' % (self.get_cloud(), parameter_name),
                          default_value)

    def get_instance_id(self):
        return self.__get(NodeDecorator.INSTANCEID_KEY)

    def get_image_id(self):
        return self.get_image_attribute('id')

    def get_image_resource_uri(self):
        return self.get_image_attribute('resourceUri')

    def get_image_short_name(self):
        return self.get_image_attribute('shortName')

    def get_image_name(self):
        return self.get_image_attribute('name')

    def get_image_version(self):
        return self.get_image_attribute('version')

    def get_image_description(self, default_value=None):
        return self.get_image_attribute('description', default_value)

    def get_volatile_extra_disk_size(self):
        return self.__get('extra.disk.volatile')

    def get_name(self):
        return self.__get(NodeDecorator.NODE_INSTANCE_NAME_KEY)

    def get_node_name(self):
        return self.__get(NodeDecorator.NODE_NAME_KEY)

    def get_network_type(self, default_value=None):
        return self.__get('network', default_value)

    def get_networks(self):
        return self.get_cloud_parameter('networks', '').split(',')

    def get_platform(self):
        return self.__get(NodeDecorator.IMAGE_PLATFORM_KEY, 'linux')

    def get_scale_state(self):
        return self.__parameters.get(NodeDecorator.SCALE_STATE_KEY)

    def get_prerecipe(self):
        return self.get_image_attribute('prerecipe', '')

    def get_recipe(self):
        return self.get_image_attribute('recipe', '')

    def get_packages(self):
        return self.get_image_attribute('packages', [])

    def get_username(self, default_value=None):
        return self.get_image_attribute('loginUser', default_value)

    def get_password(self):
        return self.get_cloud_parameter('login.password')

    def get_instance_type(self):
        return self.get_cloud_parameter('instance.type')

    def get_security_groups(self):
        security_groups = self.get_cloud_parameter(
            NodeDecorator.SECURITY_GROUPS_KEY, '').split(',')
        return [x.strip() for x in security_groups if x and x.strip()]

    def get_cpu(self):
        return self.get_cloud_parameter('cpu')

    def get_ram(self):
        return self.get_cloud_parameter('ram')

    def get_smp(self):
        return self.get_cloud_parameter('smp')

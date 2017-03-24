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


def as_list(func):
    def wfun(self):
        val = func(self)
        if val:
            if isinstance(val, list):
                return map(lambda x: x.strip(), val)
            else:
                return map(lambda x: x.strip(), val.split(','))
        else:
            return []
    return wfun


class NodeInstance(object):

    IMAGE_ATTRIBUTE_PREFIX = 'image'
    IMAGE_TARGETS_PREFIX = IMAGE_ATTRIBUTE_PREFIX + '.targets'

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
        if isinstance(value, basestring):
            value = value.strip()
        self.__parameters[parameter_name] = value

    def get_cloud(self):
        return self.__get(NodeDecorator.CLOUDSERVICE_KEY)

    def get_image_attribute(self, attribute_name, default_value=None):
        return self.__get('%s.%s' %
                          (self.IMAGE_ATTRIBUTE_PREFIX, attribute_name),
                          default_value)

    def get_image_target(self, target_name, default_value=None):
        return self.__get('%s.%s' %
                          (self.IMAGE_TARGETS_PREFIX, target_name),
                          default_value)

    def get_cloud_parameter(self, parameter_name, default_value=None):
        return self.__get('%s.%s' % (self.get_cloud(), parameter_name),
                          default_value)

    def set_attributes(self, attributes):
        """attributes: dict
        """
        for key, value in attributes.items():
            self.__set(key, value)

    def set_image_attributes(self, image_attributes):
        """image_attributes: dict
        """
        for key, value in image_attributes.items():
            self.__set('%s.%s' % (self.IMAGE_ATTRIBUTE_PREFIX, key), value)

    def set_image_targets(self, image_targets):
        """image_targets: dict
        """
        for key, value in image_targets.items():
            self.__set('%s.%s' % (self.IMAGE_TARGETS_PREFIX, key), value)

    def set_build_state(self, build_state):
        self.__set(NodeDecorator.BUILD_STATE_KEY, build_state)

    def set_cloud_parameters(self, cloud_parameters):
        for key, value in cloud_parameters.items():
            self.__set('%s.%s' % (self.get_cloud(), key), value)

    def set_parameter(self, name, value):
        self.__set(name, value)

    def is_orchestrator(self):
        is_orch = self.__get(NodeDecorator.IS_ORCHESTRATOR_KEY)

        if is_orch is None:
            return NodeDecorator.is_orchestrator_name(self.get_name())
        else:
            return util.str2bool(is_orch)

    def is_windows(self):
        return self.get_platform().lower() == 'windows'

    def get_build_state(self):
        return self.__get(NodeDecorator.BUILD_STATE_KEY, {})

    def get_instance_id(self):
        return self.__get(NodeDecorator.INSTANCEID_KEY)

    def get_image_id(self):
        return self.get_image_attribute('id')

    def get_id(self):
        return self.__get('id')

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
        return self.__get(NodeDecorator.NODE_NAME_KEY) or self.get_name()

    def get_root_disk_size(self, default_value=None):
        return self.__get('disk.GB', default_value)

    def get_network_type(self, default_value=None):
        return self.__get('network', default_value)

    @as_list
    def get_networks(self):
        "Return list of user provided network names, or an empty list instead."
        return self.get_cloud_parameter('networks', [])

    def get_platform(self):
        return self.get_image_attribute(NodeDecorator.PLATFORM_KEY, 'linux')

    def get_scale_state(self):
        return self.__parameters.get(NodeDecorator.SCALE_STATE_KEY)

    def get_prerecipe(self):
        return self.get_image_target(NodeDecorator.NODE_PRERECIPE)

    def get_recipe(self):
        return self.get_image_target(NodeDecorator.NODE_RECIPE)

    def get_packages(self):
        return self.get_image_target(NodeDecorator.NODE_PACKAGES, [])

    def get_username(self, default_value=None):
        return self.get_image_attribute(NodeDecorator.LOGIN_USER_KEY, default_value)

    def get_password(self):
        return self.get_cloud_parameter(NodeDecorator.LOGIN_PASS_KEY)

    def get_instance_type(self):
        return self.get_cloud_parameter('instance.type')

    @as_list
    def get_security_groups(self):
        "Return list of security group names, or an empty list instead."
        return self.get_cloud_parameter(NodeDecorator.SECURITY_GROUPS_KEY, [])

    def get_cpu(self):
        return self.get_cloud_parameter('cpu')

    def get_ram(self):
        return self.get_cloud_parameter('ram')

    def get_smp(self):
        return self.get_cloud_parameter('smp')

    def get_max_provisioning_failures(self):
        return self.__get(NodeDecorator.MAX_PROVISIONING_FAILURES_KEY)

    def get_disk_attach_size(self):
        return self.__get(NodeDecorator.SCALE_DISK_ATTACH_SIZE)

    def get_disk_detach_device(self):
        return self.__get(NodeDecorator.SCALE_DISK_DETACH_DEVICE)


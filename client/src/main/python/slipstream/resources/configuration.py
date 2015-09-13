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

from slipstream.util import SERVER_CONFIGURATION_BASICS_CATEGORY
from slipstream.util import SERVER_CONFIGURATION_CONNECTOR_CLASSES_KEY


def get_cloud_connector_classes(config):
    """
    :param config: representation of the configuration
    :type config: dict
    :rtype: dict
    """
    cloud_connector_classes = {}
    for p in config.get(SERVER_CONFIGURATION_BASICS_CATEGORY, []):
        if len(p) == 2:
            k, v = p
            if k == SERVER_CONFIGURATION_CONNECTOR_CLASSES_KEY:
                cloud_connector_classes = _connector_classes_str_to_dict(v)
                break
    return cloud_connector_classes

def _connector_classes_str_to_dict(classes_conf_str):
    """
    Input: 'foo:bar, baz'
    Result: {'foo': 'bar', 'baz': 'baz'}
    """
    if len(classes_conf_str) == 0:
        return {}
    classes_conf_dict = {}
    for cc in classes_conf_str.split(','):
        cc_t = cc.strip().split(':')
        if len(cc_t) == 1:
           classes_conf_dict[cc_t[0]] = cc_t[0]
        else:
           classes_conf_dict[cc_t[0]] = cc_t[1]
    return classes_conf_dict

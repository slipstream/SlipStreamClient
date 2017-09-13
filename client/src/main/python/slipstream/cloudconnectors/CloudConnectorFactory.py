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

from slipstream.util import load_module, CONFIGPARAM_CONNECTOR_MODULE_NAME
from slipstream.exceptions.Exceptions import NotFoundError


def get_connector_module_name(configHolder):
    try:
        return getattr(configHolder, CONFIGPARAM_CONNECTOR_MODULE_NAME)
    except AttributeError:
        raise NotFoundError("Failed to find module name for connector: %s\n"
                            "The connector module name should be defined in "
                            "configuration file as '%s' parameter." % (
                                configHolder.cloud,
                                CONFIGPARAM_CONNECTOR_MODULE_NAME))


class CloudConnectorFactory(object):
    @staticmethod
    def createConnector(configHolder):
        mod = load_module(get_connector_module_name(configHolder))
        return mod.getConnector(configHolder)

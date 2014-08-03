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

import re

RUN_CATEGORY_IMAGE = 'Image'
RUN_CATEGORY_DEPLOYMENT = 'Deployment'
KEY_RUN_CATEGORY = 'run_category'


class NodeDecorator(object):
    # Execution instance property namespace and separator
    globalNamespaceName = 'ss'
    NODE_PROPERTY_SEPARATOR = ':'
    globalNamespacePrefix = globalNamespaceName + NODE_PROPERTY_SEPARATOR

    ABORT_KEY = 'abort'

    # Node multiplicity index separator - e.g. <nodename>.<index>:<prop>
    NODE_MULTIPLICITY_SEPARATOR = '.'
    nodeMultiplicityStartIndex = '1'

    # Counter names
    initCounterName = globalNamespacePrefix + 'initCounter'
    finalizeCounterName = globalNamespacePrefix + 'finalizeCounter'
    terminateCounterName = globalNamespacePrefix + 'terminateCounter'

    # Orchestrator name
    orchestratorName = 'orchestrator'
    ORCHESTRATOR_NODENAME_RE = re.compile('orchestrator(-\w[-\w]*)?$')

    # Name given to the machine being built for node state
    MACHINE_NAME = 'machine'
    defaultMachineNamePrefix = MACHINE_NAME + NODE_PROPERTY_SEPARATOR

    # List of reserved and special node names
    reservedNodeNames = [globalNamespaceName, orchestratorName, MACHINE_NAME]

    NODE_NAME_KEY = 'nodename'
    NODE_INSTANCE_NAME_KEY = 'name'

    IS_ORCHESTRATOR_KEY = 'is.orchestrator'

    # State names
    STATE_KEY = 'state'
    COMPLETE_KEY = 'complete'
    STATECUSTOM_KEY = 'statecustom'

    IMAGE_PLATFORM_KEY = 'image.platform'
    SCALE_STATE_KEY = 'scale.state'
    INSTANCEID_KEY = 'instanceid'
    CLOUDSERVICE_KEY = 'cloudservice'
    SECURITY_GROUPS_KEY = 'security.groups'

    urlIgnoreAbortAttributeFragment = '?ignoreabort=true'

    SLIPSTREAM_DIID_ENV_NAME = 'SLIPSTREAM_DIID'

    IMAGE = RUN_CATEGORY_IMAGE
    DEPLOYMENT = RUN_CATEGORY_DEPLOYMENT

    MODULE_RESOURCE_URI = 'moduleResourceUri'

    @staticmethod
    def is_orchestrator_name(name):
        return True if NodeDecorator.ORCHESTRATOR_NODENAME_RE.match(name) else False

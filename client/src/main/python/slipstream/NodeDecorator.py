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
    ORCHESTRATOR_NODENAME_RE = re.compile('^' + orchestratorName + '(-\w[-\w]*)?$')

    # Name given to the machine being built for node state
    MACHINE_NAME = 'machine'
    defaultMachineNamePrefix = MACHINE_NAME + NODE_PROPERTY_SEPARATOR

    # List of reserved and special node names
    reservedNodeNames = [globalNamespaceName, orchestratorName, MACHINE_NAME]

    NODE_NAME_KEY = 'nodename'
    NODE_INSTANCE_NAME_KEY = 'node_instance_name'

    NODE_PRERECIPE = 'prerecipe'
    NODE_RECIPE = 'recipe'
    NODE_PACKAGES = 'packages'

    DEFAULT_SCRIPT_NAME = 'unnamed'

    IS_ORCHESTRATOR_KEY = 'is.orchestrator'

    # State names
    STATE_KEY = 'state'
    COMPLETE_KEY = 'complete'
    STATECUSTOM_KEY = 'statecustom'

    RECOVERY_MODE_KEY = 'recovery.mode'

    RUN_BUILD_RECIPES_KEY = 'run-build-recipes'
    PLATFORM_KEY = 'platform'
    LOGIN_USER_KEY = 'loginUser'
    LOGIN_PASS_KEY = 'login.password'
    BUILD_STATE_KEY = 'build.state'
    SCALE_STATE_KEY = 'scale.state'
    SCALE_IAAS_DONE = 'scale.iaas.done'
    SCALE_IAAS_DONE_SUCCESS = 'true'
    PRE_SCALE_DONE = 'pre.scale.done'
    PRE_SCALE_DONE_SUCCESS = 'true'
    SCALE_DISK_ATTACH_SIZE = 'disk.attach.size'
    SCALE_DISK_ATTACHED_DEVICE = 'disk.attached.device'
    SCALE_DISK_DETACH_DEVICE = 'disk.detach.device'
    INSTANCEID_KEY = 'instanceid'
    CLOUDSERVICE_KEY = 'cloudservice'
    SECURITY_GROUPS_KEY = 'security.groups'
    MAX_PROVISIONING_FAILURES_KEY = 'max-provisioning-failures'
    NATIVE_CONTEXTUALIZATION_KEY = 'native-contextualization'

    SECURITY_GROUP_ALLOW_ALL_NAME = 'slipstream_managed'
    SECURITY_GROUP_ALLOW_ALL_DESCRIPTION = 'Security group created by SlipStream which allows all kind of traffic.'

    urlIgnoreAbortAttributeFragment = '?ignoreabort=true'

    SLIPSTREAM_DIID_ENV_NAME = 'SLIPSTREAM_DIID'

    IMAGE = RUN_CATEGORY_IMAGE
    DEPLOYMENT = RUN_CATEGORY_DEPLOYMENT

    RUN_TYPE_ORCHESTRATION = 'Orchestration'
    RUN_TYPE_MACHINE = 'Machine'
    RUN_TYPE_RUN = 'Run'

    MODULE_RESOURCE_URI = 'moduleResourceUri'

    @staticmethod
    def is_orchestrator_name(name):
        return True if NodeDecorator.ORCHESTRATOR_NODENAME_RE.match(name) else False

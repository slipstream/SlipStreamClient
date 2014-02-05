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

from slipstream.exceptions import Exceptions
from slipstream.wrappers.BaseWrapper import BaseWrapper
from slipstream.util import loadModule

NODE_EXECUTORS = {
    'Machine': 'slipstream.executors.node.NodeImageExecutor',
    'Run': 'slipstream.executors.node.NodeDeploymentExecutor',
    'Orchestration': 'slipstream.executors.node.NodeDeploymentExecutor'
}


def get_executor_module_name(runType):
    try:
        return NODE_EXECUTORS[runType]
    except KeyError:
        raise Exceptions.ClientError("Unknown executor type: %s" % runType)


class NodeExecutorFactory:
    @staticmethod
    def createExecutor(configHolder):
        wrapper = BaseWrapper(configHolder)
        runType = wrapper.getRunType()

        return loadModule(get_executor_module_name(runType)). \
            getExecutor(wrapper, configHolder)

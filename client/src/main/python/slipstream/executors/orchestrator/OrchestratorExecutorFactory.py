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

from slipstream.executors.orchestrator.OrchestratorDeploymentExecutor import OrchestratorDeploymentExecutor
from slipstream.executors.orchestrator.OrchestratorImageBuildExecutor import OrchestratorImageBuildExecutor
from slipstream.exceptions import Exceptions
from slipstream.wrappers.CloudWrapper import CloudWrapper
from slipstream.NodeDecorator import RUN_CATEGORY_DEPLOYMENT, RUN_CATEGORY_IMAGE, \
    KEY_RUN_CATEGORY


class OrchestratorExecutorFactory:
    @staticmethod
    def createExecutor(configHolder):
        cloudWrapper = CloudWrapper(configHolder)
        category = cloudWrapper.getRunCategory()

        configHolder.set(KEY_RUN_CATEGORY, category)
        cloudWrapper.initCloudConnector(configHolder)

        if category == RUN_CATEGORY_IMAGE:
            return OrchestratorImageBuildExecutor(cloudWrapper, configHolder)
        elif category == RUN_CATEGORY_DEPLOYMENT:
            return OrchestratorDeploymentExecutor(cloudWrapper, configHolder)
        else:
            raise Exceptions.ClientError("Unknown category: %s" % category)

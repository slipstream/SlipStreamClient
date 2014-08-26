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

from optparse import OptionParser
import os

from slipstream import util
from slipstream.UserInfo import UserInfo
from slipstream.NodeInstance import NodeInstance
from slipstream.util import VERBOSE_LEVEL_QUIET, VERBOSE_LEVEL_DETAILED, ENV_SLIPSTREAM_SSH_PUB_KEY
from slipstream.exceptions.Exceptions import ExecutionException


class CloudClientCommand(object):

    def __init__(self):
        self.parser = None
        self.options = None
        self.args = None
        self.userInfo = None
        self.verbose_level = VERBOSE_LEVEL_QUIET

        self._init_user_info()
        self._parse_args()
        self.doWork()

    def _init_user_info(self):
        self._init_cloud_instance_name()

        self.userInfo = UserInfo(self._cloud_instance_name)

        self.userInfo['General.ssh.public.key'] = os.environ.get(ENV_SLIPSTREAM_SSH_PUB_KEY, '')

    def _parse_args(self):
        self._initParser()
        self._setCommonOptions()
        self.setProgramOptions()
        self._parse()
        self._check_default_options()
        self._checkOptions()
        self._setUserInfo()

    def _initParser(self):
        self.parser = OptionParser()
        self._set_default_options()

    def _set_default_options(self):
        self.parser.add_option('-v', dest='verbose',
                               help='Be verbose.',
                               default=False, action='store_true')

    def _setCommonOptions(self):
        raise NotImplementedError()

    def setProgramOptions(self):
        pass

    def _parse(self):
        self.options, self.args = self.parser.parse_args()

    def _check_default_options(self):
        if self.options.verbose:
            self.verbose_level = VERBOSE_LEVEL_DETAILED

    def _checkOptions(self):
        raise NotImplementedError()

    def checkOptions(self):
        pass

    def _setUserInfo(self):
        raise NotImplementedError()

    def doWork(self):
        raise NotImplementedError()

    def set_userinfo_cloud(self, params):
        self.userInfo.set_cloud_params(params)

    def _init_cloud_instance_name(self):
        try:
            self._cloud_instance_name = os.environ[util.ENV_CONNECTOR_INSTANCE]
        except KeyError:
            raise ExecutionException('Environment variable %s is required.' %
                                     util.ENV_CONNECTOR_INSTANCE)

    def get_node_instance(self):
        return NodeInstance({
            'name': os.environ.get(util.ENV_NODE_INSTANCE_NAME), #self.get_node_instance_name()
            'cloudservice': self._cloud_instance_name,
            'image.platform': self.options.platform,
            'image.imageId': self.options.imageId,
            'image.id': self.options.imageId,
            'network': 'Public'
        })






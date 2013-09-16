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

from optparse import OptionParser
import os

from slipstream.SlipStreamHttpClient import UserInfo


class CloudClientCommand(object):
    # has to be defined by sub-class
    PROVIDER_NAME = None

    def __init__(self):
        self.parser = None
        self.options = None
        self.args = None
        self.userInfo = None

        self._initUserInfo()
        self.parseArgs()
        self.doWork()

    def _initUserInfo(self):
        if not self.PROVIDER_NAME:
            raise Exception('PROVIDER_NAME has to be set.')
        self.userInfo = UserInfo(self.PROVIDER_NAME)

        os.environ['SLIPSTREAM_CONNECTOR_INSTANCE'] = self.PROVIDER_NAME

    def parseArgs(self):
        self._initParser()
        self._setCommonOptions()
        self.setProgramOptions()
        self._parse()
        self._checkOptions()
        self._setUserInfo()

    def _initParser(self):
        self.parser = OptionParser()

    def _setCommonOptions(self):
        raise NotImplementedError()

    def setProgramOptions(self):
        pass

    def _parse(self):
        self.options, self.args = self.parser.parse_args()

    def _checkOptions(self):
        raise NotImplementedError()

    def checkOptions(self):
        pass

    def _setUserInfo(self):
        raise NotImplementedError()

    def doWork(self):
        raise NotImplementedError()

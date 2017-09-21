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

import sys
import os
import traceback
from slipstream import util

from slipstream.ConfigHolder import ConfigHolder
from slipstream.api.deployment import NodeDecorator


class Machine(object):
    def __init__(self, executorFactory, configHolder=ConfigHolder()):
        self.executorFactory = executorFactory
        self.configHolder = configHolder
        configHolder.assign(self)

    def execute(self):
        try:
            executor = self.executorFactory.createExecutor(self.configHolder)
        except Exception as ex:
            self._publish_abort_and_fail("Machine executor creation failed", ex)
        executor.execute()

    def _publish_abort_and_fail(self, message, exception):
        util.printError('Failing... %s: %s' % (message, str(exception)))
        traceback.print_exc()
        AbortExceptionPublisher(self.configHolder).publish(message, sys.exc_info())
        raise exception


class AbortExceptionPublisher(object):

    @staticmethod
    def _get_verbosity_level(config_holder):
        try:
            return int(config_holder.verboseLevel)
        except:
            return int(os.environ.get('SLIPSTREAM_VERBOSITY_LEVEL', '0'))

    @staticmethod
    def _format_exception_message(message, exc_info, verbosity_level=0):
        "exc_info - three-element list as returned by sys.exc_info()"
        if verbosity_level > 1:
            msg_list = traceback.format_exception(*exc_info)
        else:
            msg_list = traceback.format_exception_only(*exc_info[:2])
        return '%s: %s' % (message, ''.join(msg_list).strip())

    def __init__(self, config_holder):
        """
        config_holder: ConfigHolder object
        """
        self.ss_client = SlipStreamHttpClient(config_holder)
        self.verbosity_level = self._get_verbosity_level(config_holder)

    def publish(self, message, exc_info):
        """Publish formatted exception as abort message on the Run.
        message: string
        exc_info: three-element list as returned by sys.exc_info()
        """
        msg = self._format_exception_message(message, exc_info, self.verbosity_level)
        self._publish_abort(msg)

    def _publish_abort(self, message):
        self.ss_client.ignoreAbort = True
        abort = NodeDecorator.GLOBAL_NS + \
                NodeDecorator.NODE_PROPERTY_SEPARATOR + NodeDecorator.ABORT_KEY
        self.ss_client.setRuntimeParameter(abort, message)

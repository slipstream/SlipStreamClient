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

import os
import sys
import signal
from optparse import OptionParser

from slipstream import util
from slipstream.UserInfo import UserInfo
from slipstream.util import VERBOSE_LEVEL_QUIET, VERBOSE_LEVEL_DETAILED, ENV_SLIPSTREAM_SSH_PUB_KEY
from slipstream.exceptions.Exceptions import ExecutionException


class VerboseException(Exception):

    def __init__(self, cause):
        self.cause = cause
        self.traceback = sys.exc_info()

    def __str__(self):
        return str(self.cause)


def main(command):
    try:
        command().execute()
        exit(0)
    except KeyboardInterrupt:
        print '\n\nExecution interrupted by the user... goodbye!'
        exit(1)
    except VerboseException as e:
        exc_info = e.traceback
        raise exc_info[0], exc_info[1], exc_info[2]
    except Exception as e:
        print >> sys.stderr, e
        exit(2)


class CloudClientCommand(object):

    ''' Methods that can/should be reimplemented '''

    def get_connector_class(self):
        raise NotImplementedError()

    def get_cloud_specific_user_cloud_params(self):
        return {}

    def set_cloud_specific_options(self, parser):
        pass

    def get_cloud_specific_mandatory_options(self):
        return []

    def get_initialization_extra_kwargs(self):
        return {}

    ''' ---------------------------------------- '''

    def do_work(self):
        raise NotImplementedError()

    def _get_default_timeout(self):
        raise NotImplementedError()

    def _set_command_specific_options(self, parser):
        pass

    def _get_command_specific_user_cloud_params(self):
        return {}

    def _get_command_mandatory_options(self):
        return []

    def alarm_handler(self, signum, frame):
        raise RuntimeError('The command has timed out.')

    def __init__(self):
        self.parser = None
        self.options = None
        self.args = None
        self.user_info = None
        self.verbose_level = VERBOSE_LEVEL_QUIET
        self.mandatory_options = []
        self.timeout = None
        self._init_args_parser()

    def execute(self):
        self._parse_args()
        self._init_cloud_instance_name()
        try:
            self._init_user_info()

            if self.timeout:
                signal.signal(signal.SIGALRM, self.alarm_handler)
                signal.alarm(self.timeout)
            self.do_work()
        except Exception as e:
            if self.get_option('verbose'):
                raise VerboseException(e)
            else:
                raise

    def _init_user_info(self):
        self.user_info = UserInfo(self._cloud_instance_name)
        self.user_info['General.ssh.public.key'] = os.environ.get(ENV_SLIPSTREAM_SSH_PUB_KEY, '')

        self.user_info.set_cloud_params(self._get_common_user_cloud_params())
        self.user_info.set_cloud_params(self._get_command_specific_user_cloud_params())
        self.user_info.set_cloud_params(self.get_cloud_specific_user_cloud_params())

    def _init_args_parser(self):
        self._init_parser()

        self._set_common_options(self.parser)
        self._set_command_specific_options(self.parser)
        self.set_cloud_specific_options(self.parser)

        self._add_mandatory_options(self.get_cloud_specific_mandatory_options())
        self._add_mandatory_options(self._get_common_mandatory_options())
        self._add_mandatory_options(self._get_command_mandatory_options())

    def _parse_args(self):
        self._parse()
        self._check_options()

    def _init_parser(self):
        self.parser = OptionParser()
        self._set_default_options()

    def _add_mandatory_options(self, mandatory_options):
        self.mandatory_options += mandatory_options

    def _get_common_mandatory_options(self):
        return [UserInfo.CLOUD_USERNAME_KEY,
                UserInfo.CLOUD_PASSWORD_KEY]

    def _set_default_options(self):
        self.parser.add_option('-v', dest='verbose', help='Be verbose.', default=False, action='store_true')
        self.parser.add_option('-t', dest='timeout', help='Timeout (in seconds). Default: %s' %
                               self._get_default_timeout(), default=self._get_default_timeout(), type='int')

    def _set_common_options(self, parser):
        parser.add_option('--' + UserInfo.CLOUD_USERNAME_KEY, dest=UserInfo.CLOUD_USERNAME_KEY,
                          help='Cloud username', metavar='USERNAME',
                          default=os.environ.get('__SLIPSTREAM_CLOUD_USERNAME', ''))
        parser.add_option('--' + UserInfo.CLOUD_PASSWORD_KEY, dest=UserInfo.CLOUD_PASSWORD_KEY,
                          help='Cloud password', metavar='PASSWORD',
                          default=os.environ.get('__SLIPSTREAM_CLOUD_PASSWORD', ''))

    def get_option(self, name):
        return getattr(self.options, name)

    def _parse(self):
        self.options, self.args = self.parser.parse_args()

    def _check_default_options(self):
        if self.options.verbose:
            self.verbose_level = VERBOSE_LEVEL_DETAILED

        self.timeout = self.options.timeout

    def _check_options(self):
        missing_list = [name for name in self.mandatory_options
                        if not getattr(self.options, name, None)]
        if missing_list:
            missing_options = ', '.join(map(lambda x: '--' + x, missing_list))
            self.parser.error('The following mandatory options were not provided: %s' %
                              missing_options)

        self._check_default_options()

    def _get_common_user_cloud_params(self):
        return {
            UserInfo.CLOUD_USERNAME_KEY: self.get_option(UserInfo.CLOUD_USERNAME_KEY),
            UserInfo.CLOUD_PASSWORD_KEY: self.get_option(UserInfo.CLOUD_PASSWORD_KEY)
        }

    def doWork(self):
        raise NotImplementedError()

    def set_userinfo_cloud(self, params):
        self.user_info.set_cloud_params(params)

    def _init_cloud_instance_name(self):
        self._cloud_instance_name = util.get_required_envvar(util.ENV_CONNECTOR_INSTANCE)

    def get_node_instance_name(self):
        return util.get_required_envvar(util.ENV_NODE_INSTANCE_NAME)

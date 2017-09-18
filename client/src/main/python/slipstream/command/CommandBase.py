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
from __future__ import print_function

import os
import sys
import traceback
from optparse import OptionParser

from slipstream import __version__
import slipstream.util as util
from slipstream.api.cimi import CIMI
from slipstream.api.http import SessionStore
from slipstream.exceptions.Exceptions import NotYetSetException
from slipstream.api.exceptions import SlipStreamError

etree = util.importETree()

if 'SLIPSTREAM_HOME' in os.environ:
    slipstreamHome = os.environ['SLIPSTREAM_HOME']
else:
    slipstreamHome = os.path.dirname(__file__)

slipstreamDirName = 'slipstream'
binDirName = 'bin'
repDirName = 'repository'
repDir = os.path.join(slipstreamDirName, repDirName)


def set_env():
    newEnv = \
        '.' + os.pathsep + \
        os.path.join(slipstreamHome, 'bin')
    if os.getenv('PYTHONPATH'):
        os.environ['PYTHONPATH'] = newEnv + os.pathsep + os.environ['PYTHONPATH']
    else:
        os.environ['PYTHONPATH'] = newEnv


def set_path():
    sys.path.insert(1, '.')
    set_env()


set_path()

try:
    from slipstream.exceptions.Exceptions import NetworkError
    from slipstream.exceptions.Exceptions import ServerError
    from slipstream.exceptions.Exceptions import SecurityError
    from slipstream.exceptions.Exceptions import AbortException
    from slipstream.exceptions.Exceptions import ClientError
    from slipstream.exceptions.Exceptions import TimeoutException

    util.slipstreamHome = slipstreamHome
except KeyboardInterrupt:
    print('\nExecution interrupted by the user... goodbye!')
    sys.exit(-1)


class CommandBase(object):

    exc_to_exit_code = {NotYetSetException: 1,
                        ValueError: 3,
                        ServerError: 5,
                        ClientError: 7,
                        AbortException: 8,
                        TimeoutException: 9,
                        SlipStreamError: 10}
    def __init__(self):

        self.username = None
        self.endpoint = None
        self.password = None
        self._cimi = None
        self.verboseLevel = 0
        self.options = None
        self.args = None
        self.parser = None
        self._setParserAndParse()

        self.userProperties = {}
        self.userEnv = {}
        self.version = False
        self.noemail = False

        util.PRINT_TO_STDERR_ONLY = True

        util.printDetail("Calling: '%s'" % ' '.join(sys.argv), self.verboseLevel)
        self._callAndHandleErrorsForCommands(self.do_work.__name__)

        util.PRINT_TO_STDERR_ONLY = False

    def _setParserAndParse(self):
        self.parser = OptionParser()
        self.parser.add_option('-v', '--verbose', dest='verboseLevel',
                               help='verbose level. Add more to get more details.',
                               action='count', default=self.verboseLevel)
        self.parse()
        self.verboseLevel = self.options.verboseLevel

    def add_authentication_options(self):
        self.parser.add_option('-u', '--username', dest='username',
                               help='SlipStream username or $SLIPSTREAM_USERNAME',
                               metavar='USERNAME',
                               default=os.environ.get('SLIPSTREAM_USERNAME'))
        self.parser.add_option('-p', '--password', dest='password',
                               help='SlipStream password or $SLIPSTREAM_PASSWORD',
                               metavar='PASSWORD',
                               default=os.environ.get('SLIPSTREAM_PASSWORD'))
        self.parser.add_option('--insecure', dest='insecure',
                               help='When set, client will skip the '
                                    'validation of server certificate.',
                               default=False, action='store_true')
        self.add_cookie_option()

    def add_cookie_option(self):
        default_cookie = util.DEFAULT_COOKIE_FILE
        self.parser.add_option('--cookie', dest='cookie_filename',
                               help='SlipStream cookie. Default: %s' %
                                    default_cookie, metavar='FILE',
                               default=default_cookie)

    def add_endpoint_option(self):
        default = 'https://nuv.la'
        effective_default = os.environ.get('SLIPSTREAM_ENDPOINT', default)
        self.parser.add_option('--endpoint', dest='endpoint', metavar='URL',
                               help='SlipStream server endpoint. Default: '
                                    '$SLIPSTREAM_ENDPOINT or %s' % default,
                               default=effective_default)

    def parse(self):
        pass

    def addIgnoreAbortOption(self):
        self.parser.add_option('--ignore-abort', dest='ignoreAbort',
                               help='by default, if the run abort flag is set, any \
                               call will return with an error. With this option values \
                               can be queried even if the abort flag is raised',
                               default=False, action='store_true')

    def _callAndHandleErrorsForCommands(self, methodName, *args, **kw):
        res = 0
        try:
            res = self.__class__.__dict__[methodName](self, *args, **kw)
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as ex:
            self._exit(ex)
        return res

    def _exit(self, ex):
        """
        :param ex: Exception object or string
        :return:
        """
        if self.verboseLevel > 1:
            sys.stderr.writelines(traceback.format_exc())
        msg = str(ex)
        try:
            # Old style error message in the HTTP body as xml.
            error = self._read_as_xml(str(ex))
            msg = '{}: {} - {}'.format(
                error.get('detail'), error.get('code'), error.get('reason'))
        except:
            pass
        sys.stderr.writelines("ERROR: %s\n" % msg)
        if isinstance(ex, Exception):
            sys.exit(self.exc_to_exit_code.get(ex, 1))
        else:
            sys.exit(1)

    def _getHomeDirectory(self):
        return util.getHomeDirectory()

    def parseCommandLineProperties(self, value):
        bits = value.split('=')
        if len(bits) != 2:
            self.usageExit("Error: properties must be expressed as: <name>=<value>, got '%s'" % value)

        # Type convertions
        if bits[1].lower() == 'true':
            bits[1] = True
        elif bits[1].lower() == 'false':
            bits[1] = False
        else:
            if bits[1].isdigit():
                try:
                    bits[1] = int(bits[1])
                except ValueError:
                    pass

        self.userProperties[bits[0]] = bits[1]

        return bits[0], bits[1]

    def parseCommandLineEnv(self, value):
        bits = value.split('=')
        if len(bits) == 0 or len(bits) > 2:
            self.usageExit("Error: environment variables must be expressed as: "
                           "<name>=<value>, got '%s'" % value)
        self.userEnv[bits[0]] = bits[1]

        return bits[0], bits[1]

    def usageExitTooFewArguments(self):
        return self.usageExit('Too few arguments')

    def usageExitTooManyArguments(self):
        return self.usageExit('Too many arguments')

    def usageExitWrongNumberOfArguments(self):
        return self.usageExit('Wrong number of arguments')

    def usageExitNoArgumentsRequired(self):
        return self.usageExit('No arguments required')

    def usageExit(self, msg=None):
        self.parser.print_help()
        print('')
        print('got: ' + ' '.join(sys.argv))
        if msg:
            self._exit(msg)
        else:
            sys.exit(1)

    def getVersion(self):
        print(__version__.getPrettyVersion())

    def log(self, message):
        util.printDetail(message, self.verboseLevel)

    def parse_xml_or_exit_on_error(self, xml):
        try:
            return self._read_as_xml(xml)
        except Exception as ex:
            print(str(ex))
            if self.verboseLevel:
                raise
            sys.exit(-1)

    def _read_as_xml(self, xml):
        return etree.fromstring(xml)

    def read_input_file(self, ifile):
        self.check_is_file(ifile)
        return open(ifile).read()

    def check_is_file(self, file):
        if not os.path.exists(file):
            self.usageExit("Unknown filename: " + file)
        if not os.path.isfile(file):
            self.usageExit("Input is not a file: " + file)

    @property
    def cimi(self):
        if not self._cimi:
            http = SessionStore(cookie_file=self.options.cookie_filename,
                                insecure=self.options.insecure,
                                log_http_detail=(self.options.verboseLevel >= 3))
            cimi = CIMI(http, endpoint=self.options.endpoint)
            cimi.login_internal(self.username, self.password)
            self._cimi = cimi
        return self._cimi

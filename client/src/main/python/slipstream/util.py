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

import contextlib
import logging
import os
import pkgutil
import subprocess
import sys
import tempfile
import time
import urllib2
import uuid as uuidModule
import warnings
from itertools import chain
from ConfigParser import SafeConfigParser

import slipstream.exceptions.Exceptions as Exceptions

timeformat = '%Y-%m-%d %H:%M:%S'

VERBOSE_LEVEL_QUIET = 0
VERBOSE_LEVEL_NORMAL = 1
VERBOSE_LEVEL_DETAILED = 2

PRINT_TO_STDERR_ONLY = False

TMPDIR = os.path.join(tempfile.gettempdir(), 'slipstream')
REPORTSDIR = os.environ.get('SLIPSTREAM_REPORT_DIR',
                            os.path.join(os.sep, TMPDIR, 'reports'))
WINDOWS_REPORTSDIR = '%TMP%\\slipstream\\reports'
HTTP_CACHEDIR = os.path.join(tempfile.gettempdir(), '.ss_http_cache')

RUN_RESOURCE_PATH = '/run'
MODULE_RESOURCE_PATH = '/module'
USER_RESOURCE_PATH = '/user'

CONFIGPARAM_CONNECTOR_MODULE_NAME = 'cloudconnector'

SUPPORTED_PLATFORMS_BY_DISTRO = {'debian_based': ('ubuntu',),
                                 'redhat_based': ('fedora', 'redhat', 'centos')}
SUPPORTED_PLATFORMS = [y for x in SUPPORTED_PLATFORMS_BY_DISTRO.values() for y in x]

ENV_NEED_TO_ADD_SSHPUBKEY = 'SLIPSTREAM_NEED_TO_ADD_SSHPUBKEY'


def get_cloudconnector_modulenames(base_package='slipstream.cloudconnectors'):
    module_names = []
    pkgwalk = pkgutil.walk_packages(path=loadModule(base_package).__path__,
                                    prefix=base_package + '.')
    for _, pkgname, ispkg in pkgwalk:
        if ispkg:
            mdlwalk = pkgutil.iter_modules(path=loadModule(pkgname).__path__,
                                           prefix=pkgname + '.')
            for _, name, ispkg in mdlwalk:
                if not ispkg:
                    if hasattr(loadModule(name), 'getConnector'):
                        module_names.append(name)
    return module_names


def get_cloudconnector_modulename_by_cloudname(cloudname):
    for module_name in get_cloudconnector_modulenames():
        connector_class = loadModule(module_name).getConnectorClass()
        if getattr(connector_class, 'cloudName') == cloudname:
            return module_name
    raise Exceptions.NotFoundError(
        "Failed to find cloud connector module for cloud %s." % cloudname)


def needToAddSshPubkey():
    return (os.environ.get(ENV_NEED_TO_ADD_SSHPUBKEY, '').lower() == 'true') \
        and not is_windows()


def configureLogger():
    filename = os.path.join(os.path.abspath(os.path.dirname(sys.argv[0])),
                            'slipstream.log')
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(levelname)s %(message)s',
                        filename=filename)


def is_windows():
    return sys.platform == 'win32'


def execute(commandAndArgsList, **kwargs):
    wait = not kwargs.pop('noWait', False)

    withStderr = kwargs.pop('withStderr', False)
    withStdOutErr = kwargs.pop('withOutput', False)
    # Getting stderr takes precedence on getting stdout&stderr.
    if withStderr:
        kwargs['stderr'] = subprocess.PIPE
        withStdOutErr = False

    if withStdOutErr:
        kwargs['stdout'] = subprocess.PIPE
        kwargs['stderr'] = subprocess.STDOUT
        kwargs['close_fds'] = True

    if is_windows():
        commandAndArgsList.insert(0, '-File')
        commandAndArgsList.insert(0, 'Bypass')
        commandAndArgsList.insert(0, '-ExecutionPolicy')
        commandAndArgsList.insert(0, 'powershell')

    if isinstance(commandAndArgsList, list):
        _cmd = ' '.join(commandAndArgsList)
    else:
        _cmd = commandAndArgsList

    printDetail('Calling: %s' % _cmd, kwargs)

    if isinstance(commandAndArgsList, list) and kwargs.get('shell', False):
        commandAndArgsList = ' '.join(commandAndArgsList)

    extra_env = kwargs.pop('extra_env', {})
    if extra_env:
        kwargs['env'] = dict(chain(os.environ.copy().iteritems(),
                                   extra_env.iteritems()))
    process = subprocess.Popen(commandAndArgsList, **kwargs)

    if not wait:
        return process

    output, errors = process.communicate()

    if withStderr:
        return process.returncode, errors
    elif withStdOutErr:
        return process.returncode, output
    else:
        return process.returncode


def removeLogger(handler):
    logger = logging.getLogger()
    logger.removeHandler(handler)


def redirectStd2Logger():
    configureLogger()
    sys.stderr = StdOutWithLogger('stderr')
    sys.stdout = StdOutWithLogger('stdout')


def resetStdFromLogger():
    sys.stdout = sys.stdout._std
    sys.stderr = sys.stderr._std


def redirectStd2File(filename):
    sys.stderr = StdOutWithFile(filename)
    sys.stdout = StdOutWithFile(filename)


def resetStdFromFile():
    sys.stdout = sys.stdout._stdout
    sys.stderr = sys.stderr._stderr


def whoami():
    return sys._getframe(1).f_code.co_name


class StdOutWithFile(object):
    def __init__(self, filename):
        self._stdout = sys.stdout
        self._stderr = sys.stderr
        self.fh = file(filename, 'w')

    def __del__(self):
        self.flush()
        self.fh.close()

    def writelines(self, msgs):
        # Test if msgs is a list or not
        try:
            msgs.append('')
        except AttributeError:
            # It's probably a string, so we write it directly
            self.write(msgs + '\n')
            return
        for msg in msgs:
            self.write(msg)
        self.flush()

    def write(self, _string):
        _string = unicode(_string).encode('utf-8')
        self._stdout.write(_string)
        self.fh.write(_string)
        self.flush()

    def flush(self):
        self._stdout.flush()
        self.fh.flush()


class StdOutWithLogger:
    def __init__(self, std):
        if std == 'stdout':
            self._std = sys.stdout
            self.logType = 'out'
        elif std == 'stderr':
            self._std = sys.stderr
            self.logType = 'err'
        else:
            raise ValueError('Unknown std type: %s' % std)

    def writelines(self, msgs):
        # Test if msgs is a list or not
        try:
            msgs.append('')
        except AttributeError:
            # It's probably a string, so we write it directly
            self.write(msgs + '\n')
            return
        for msg in msgs:
            self.write(msg)
        return

    def write(self, string):
        _string = unicode(string).encode('utf-8')
        self._std.write(_string)
        if string == '.':
            return
        if self.logType == 'out':
            logging.info(_string)
        else:
            logging.error(_string)
        return

    def flush(self):
        self._std.flush()


def getHomeDirectory():
    if (sys.platform == "win32"):
        if "HOME" in os.environ:
            return os.environ["HOME"]
        elif "USERPROFILE" in os.environ:
            return os.environ["USERPROFILE"]
        else:
            return "C:\\"
    else:
        if "HOME" in os.environ:
            return os.environ["HOME"]
        else:
            # No home directory set
            return ""


def getConfigFileName():
    ''' Look for the configuration file in the following order:
        1- local directory
        2- installation location
        3- calling module location
    '''
    filename = 'slipstream.client.conf'
    try:
        configFilename = os.path.join(os.getcwd(), filename)
    except OSError:  # current directory may no longer exists
        configFilename = os.path.join(getInstallationLocation(), filename)
    if os.path.exists(configFilename):
        return configFilename
    configFilename = os.path.join(os.path.dirname(sys.argv[0]), filename)
    if os.path.exists(configFilename):
        return configFilename
    raise Exceptions.ConfigurationError(
        "Failed to find the configuration file: " + configFilename)


def getInstallationLocation():
    ''' Look for the installation location in the following order:
        1- SLIPSTREAM_HOME env var if set
        2- Default target directory, if exists (/opt/slipstream/src)
        3- Base module: __file__/../../.., since the util module is namespaced
    '''
    if 'SLIPSTREAM_HOME' in os.environ:
        return os.environ['SLIPSTREAM_HOME']

    slipstreamDefaultDirName = os.path.join(os.sep, 'opt', 'slipstream', 'client',
                                            'src')
    if os.path.exists(slipstreamDefaultDirName):
        return slipstreamDefaultDirName

    # Relative to the src dir.  We do this to avoid importing a module, since util
    # should have a minimum of dependencies
    return os.path.join(os.path.dirname(__file__), '..', '..', '..')


def uuid():
    '''Generates a unique ID.'''
    return str(uuidModule.uuid4())


def printDetail(message, verboseLevel=1, verboseThreshold=1, timestamp=True):
    if verboseLevel >= verboseThreshold:
        printAndFlush('\n    %s\n' % message, timestamp=timestamp)


def _printDetail(message, kwargs={}):
    verboseLevel = _extractVerboseLevel(kwargs)
    verboseThreshold = _extractVerboseThreshold(kwargs)
    timestamp = _extractTimestamp(kwargs)
    printDetail(message, verboseLevel, verboseThreshold, timestamp)


def _extractVerboseLevel(kwargs):
    return _extractAndDeleteKey('verboseLevel', 0, kwargs)


def _extractVerboseThreshold(kwargs):
    return _extractAndDeleteKey('verboseThreshold', 2, kwargs)


def _extractTimestamp(kwargs):
    return _extractAndDeleteKey('timestamp', False, kwargs)


def _extractAndDeleteKey(key, default, dictionary):
    value = default
    if key in dictionary:
        value = dictionary[key]
        del dictionary[key]
    return value


def printAction(message):
    length = len(message)
    padding = 4 * '='
    line = (length + 2 * len(padding) + 2) * '='
    _message = padding + ' %s ' % message + padding
    printAndFlush('\n%s\n%s\n%s\n' % (line, _message, line))


def printStep(message):
    printAndFlush('\n==== %s\n' % message)


def printAndFlush(message, timestamp=True):
    if timestamp:
        message = _prepend_current_time_to_message(message)
    output = _get_print_stream()
    output.flush()
    _print(output, message)
    output.flush()


def printError(message):
    message = _prepend_current_time_to_message('\nERROR: %s\n' % message)
    sys.stdout.flush()
    sys.stderr.flush()
    _print(sys.stderr, message)
    sys.stdout.flush()
    sys.stderr.flush()


def _print(stream, message):
    try:
        print >> stream, message,
    except UnicodeEncodeError:
        if not isinstance(message, unicode):
            message = unicode(message, 'UTF-8')
        message = message.encode('ascii', 'ignore')
        print >> stream, message,


def _get_print_stream():
    if PRINT_TO_STDERR_ONLY:
        return sys.stderr
    else:
        return sys.stdout


def _prepend_current_time_to_message(msg):
    return '\n: %s : %s' % (toTimeInIso8601(time.time()), msg)


def assignAttributes(obj, dictionary):
    for key, value in dictionary.items():
        setattr(obj, key, value)


def loadModule(moduleName):
    namespace = ''
    name = moduleName
    if name.find('.') != -1:
        # There's a namespace so we take it into account
        namespace = '.'.join(name.split('.')[:-1])

    return __import__(name, fromlist=namespace)


def parseConfigFile(filename, preserve_case=True):
    parser = SafeConfigParser()
    if preserve_case:
        parser.optionxform = str
    parser.read(filename)
    return parser


def toTimeInIso8601(_time):
    "Convert int or float to time in iso8601 format."
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(_time))


def toTimeInIso8601NoColon(_time):
    return toTimeInIso8601(_time).replace(':', '')


def filePutContent(filename, data):
    _printDetail('Creating file %s with content: \n%s\n' % (filename, data))
    fd = open(filename, 'wb')
    fd.write(data)
    fd.close()


def file_put_content_in_temp_file(data):
    _, filename = tempfile.mkstemp()
    filePutContent(filename, data)
    return filename


def fileAppendContent(filename, data):
    fd = open(filename, 'a')
    fd.write(data)
    fd.close()


def fileGetContent(filename):
    fd = open(filename, 'rb')
    content = fd.read()
    fd.close()
    return content


def importETree():
    try:
        from lxml import etree
    except ImportError:
        try:
            # Python 2.5
            import xml.etree.ElementTree as etree
        except ImportError:
            try:
                # Python 2.5
                import xml.etree.cElementTree as etree
            except ImportError:
                try:
                    # normal cElementTree install
                    import cElementTree as etree
                except ImportError:
                    try:
                        # normal ElementTree install
                        import elementtree.ElementTree as etree
                    except ImportError:
                        raise Exception("Failed to import ElementTree "
                                        "from any known place")
    return etree


def removeASCIIEscape(data):
    if hasattr(data, 'replace'):
        return data.replace('\x1b', '')
    else:
        return data


def _waitMachineNetworkUpOrAbort(host, instanceId, timeout=60):
    host_coords = "(id=%s, ip=%s)" % (host, instanceId)
    printStep("Waiting for machine network to start: %s" % host_coords)
    if not waitUntilPingOrTimeout(host, timeout):
        msg = 'Unable to ping VM in %i seconds: %s' % (timeout, host_coords)
        raise Exceptions.ExecutionException(msg)


def waitUntilPingOrTimeout(host, timeout, ticks=True, stdout=None, stderr=None):
    if not stdout:
        stdout = open('/dev/null', 'w')
    if not stderr:
        stderr = open('/dev/null', 'w')

    start = time.time()
    hostUp = False
    while not hostUp:
        if ticks:
            sys.stdout.flush()
            sys.stdout.write('.')
        hostUp = ping(host, stdout=stdout, stderr=stderr)
        sleep(1)

        if time.time() - start > timeout:
            if ticks:
                sys.stdout.flush()
                sys.stdout.write('\n')
            return False

    if ticks:
        sys.stdout.flush()
        sys.stdout.write('\n')
    return hostUp


def ping(host, timeout=5, number=1, **kwargs):
    p = subprocess.Popen(['ping', '-q', '-c', str(number), host], **kwargs)
    p.wait()
    success = (p.returncode == 0)
    return success


def sleep(seconds):
    time.sleep(seconds)


def _getSecureHostPortFromUrl(endpoint):
    scheme, netloc, _, _, _, _ = urllib2.urlparse.urlparse(endpoint)
    if scheme == 'http' or not scheme:
        secure = False
    elif scheme == 'https':
        secure = True
    else:
        raise ValueError('Unknown scheme %s' % scheme)
    if ":" in netloc:
        host, port = netloc.split(':')
    else:
        host = netloc
        port = None
    return secure, host, port


def getPackagesInstallCommand(platform, packages):
    if platform.lower() not in SUPPORTED_PLATFORMS:
        raise ValueError("Unsupported platform '%s' while installing packages. "
                         "Supported: %s" % (platform,
                                            ', '.join(SUPPORTED_PLATFORMS)))

    if platform.lower() in SUPPORTED_PLATFORMS_BY_DISTRO['debian_based']:
        cmd = 'apt-get -y install'
    elif platform.lower() in SUPPORTED_PLATFORMS_BY_DISTRO['redhat_based']:
        cmd = 'yum -y install'
    cmd += ' ' + packages
    return cmd


def appendSshPubkeyToAuthorizedKeys(pubkey):
    dot_ssh_path = os.path.expanduser('~') + '/.ssh'
    try:
        os.mkdir(dot_ssh_path)
    except:
        pass
    fileAppendContent(dot_ssh_path + '/authorized_keys',
                      '\n' + pubkey)
    execute('restorecon -R %s || true' % dot_ssh_path, noWait=True, shell=True, withStderr=True,
            withOutput=True)



class NullFile(object):
    def write(self, x):
        pass

    def flush(self):
        pass


@contextlib.contextmanager
def nostdout():
    save_stdout = sys.stdout
    try:
        sys.stdout = NullFile()
        yield
    finally:
        sys.stdout = save_stdout


@contextlib.contextmanager
def nostderr():
    save_stderr = sys.stderr
    try:
        sys.stderr = NullFile()
        yield
    finally:
        sys.stderr = save_stderr


@contextlib.contextmanager
def nostdouterr(override=False):
    save_stdout = sys.stdout
    save_stderr = sys.stderr
    try:
        if not override:
            sys.stdout = NullFile()
            sys.stderr = NullFile()
        yield
    finally:
        sys.stdout = save_stdout
        sys.stderr = save_stderr


def deprecated(func):
    """This is a decorator which can be used to mark functions as deprecated.
    It will result in a warning being emitted when the function is used."""

    def new_func(*args, **kwargs):
        warnings.warn("Call to deprecated function %s." % func.__name__,
                      category=DeprecationWarning, stacklevel=2)
        return func(*args, **kwargs)

    # warnings.simplefilter('default', DeprecationWarning)
    new_func.__name__ = func.__name__
    new_func.__doc__ = func.__doc__
    new_func.__dict__.update(func.__dict__)
    return new_func


def override(func):
    """This is a decorator which can be used to check that a method override a method of the base class.
    If not the case it will result in a warning being emitted."""

    def overrided_func(self, *args, **kwargs):
        if func.__name__ not in dir(self.__class__.__bases__[0]):
            warnings.warn("The method '%s' should override a method of the base class '%s'." %
                          (func.__name__, self.__class__.__bases__[0].__name__), category=SyntaxWarning, stacklevel=2)
        return func(self, *args, **kwargs)

    return overrided_func


def str2bool(v):
    return v.lower() in ("yes", "true", "t", "1")


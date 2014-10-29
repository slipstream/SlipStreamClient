#!/usr/bin/env python
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

import sys
import os
import tarfile
import httplib
import ssl
import urllib2
import socket
import shutil
import subprocess
import tempfile
import commands
import traceback

SLIPSTREAM_CLIENT_HOME = os.path.join(os.sep, 'opt', 'slipstream', 'client')

INSTALL_CMD = None
DISTRO = None
PIP_INSTALLED = False


class HTTPSConnection(httplib.HTTPSConnection):
    def connect(self):
        """Connect to a host on a given (SSL) port.

        Switching SSL protocol from SSLv23 to SSLv3 and TLSv1 as last resort
        when a violation of protocol occurred.
        See: http://bugs.python.org/issue11220
        """
        sock = socket.create_connection((self.host, self.port), self.timeout)
        if self._tunnel_host:
            self.sock = sock
            self._tunnel()
        try:
            # using TLSv1
            self.sock = ssl.wrap_socket(sock, self.key_file, self.cert_file,
                                        ssl_version=ssl.PROTOCOL_TLSv1)
        except ssl.SSLError:
            # switching to SSLv23
            self.sock = ssl.wrap_socket(sock, self.key_file, self.cert_file,
                                        ssl_version=ssl.PROTOCOL_SSLv23)


class HTTPSHandler(urllib2.HTTPSHandler):
    def https_open(self, req):
        return self.do_open(HTTPSConnection, req)

urllib2.install_opener(urllib2.build_opener(HTTPSHandler()))


def _setPythonpathSlipStream():
    ss_lib = os.path.join(SLIPSTREAM_CLIENT_HOME, 'lib')
    __pythonpathPrepend(ss_lib)
    sys.path.append(ss_lib)


def _setPathSlipStream():
    for p in ['bin', 'sbin']:
        __pathPrepend(os.path.join(SLIPSTREAM_CLIENT_HOME, p))


def _buildContextAndConfigSlipStream(cloud, orchestration):
    _persistSlipStreamContext(cloud)
    _persistSlipStreamConfig(cloud, orchestration)


def _persistSlipStreamContext(cloud):
    contextFile = os.path.join(tempfile.gettempdir(), 'slipstream.context')
    slipstreamContext = """[contextualization]
diid = %s
username = %s
cookie = %s
serviceurl = %s
node_instance_name = %s
""" % (os.environ['SLIPSTREAM_DIID'],
       os.environ['SLIPSTREAM_USERNAME'],
       os.environ['SLIPSTREAM_COOKIE'].strip('"'),
       os.environ['SLIPSTREAM_SERVICEURL'],
       os.environ['SLIPSTREAM_NODENAME'])
    file(contextFile, 'w').write(slipstreamContext)


def _persistSlipStreamConfig(cloud, orchestration):
    cloudConnector = os.environ.get('CLOUDCONNECTOR_PYTHON_MODULENAME', '')
    # cloud connector module name is only required for orchestration
    if not cloudConnector and orchestration:
        raise RuntimeError("Failed to find connector module name for cloud: %s" % cloud)

    clientConfig = """[System]
cloudconnector = %s
#storageconnector = slipstream.connectors.LocalCloudStorageConnector
contextualizationconnector = slipstream.connectors.LocalContextualizer
""" % cloudConnector
    for _dir in ['bin', 'sbin']:
        clientConfigFile = os.path.join(SLIPSTREAM_CLIENT_HOME, _dir, 'slipstream.client.conf')
        file(clientConfigFile, 'w').write(clientConfig)


def __pythonpathPrepend(path):
    __envPathPrepend('PYTHONPATH', path)


def __pathPrepend(path):
    __envPathPrepend('PATH', path)


def __envPathPrepend(envvar, path):
    pathList = os.environ.get(envvar, '').split(os.pathsep)
    pathList.insert(0, path)
    os.environ[envvar] = os.pathsep.join(pathList)


def _downloadAndExtractTarball(tarbalUrl, targetDir):
    try:
        remoteFile = urllib2.urlopen(tarbalUrl)
    except Exception as ex:
        print 'Failed contacting:', tarbalUrl, ' with error:"', ex, '" retrying...'
        remoteFile = urllib2.urlopen(tarbalUrl)

    try:
        shutil.rmtree(targetDir, ignore_errors=True)
        os.makedirs(targetDir)
    except OSError:
        pass

    localTarBall = os.path.join(targetDir, os.path.basename(tarbalUrl))
    targetFile = open(localTarBall, 'wb')
    while True:
        data = remoteFile.read()
        if not data:
            break
        targetFile.write(data)
    remoteFile.close()
    targetFile.close()

    print 'Expanding tarball:', localTarBall
    tarfile.open(localTarBall, 'r:gz').extractall(targetDir)


def _deployRemoteTarball(url, extract_to, name):
    print 'Retrieving %s library from %s' % (name, url)
    _downloadAndExtractTarball(url, extract_to)
    __pythonpathPrepend(extract_to)


def _setInstallCommandAndDistro():
    global INSTALL_CMD, DISTRO

    if not INSTALL_CMD or not DISTRO:
        for pkgmngr in ['apt-get', 'yum']:
            try:
                subprocess.check_call([pkgmngr, '-h'], stdout=subprocess.PIPE)
            except (subprocess.CalledProcessError, OSError):
                pass
            else:
                # TODO: on Ubuntu 10.04 there is no subprocess.check_output()!!!
                install_cmd = commands.getoutput('which %s' % pkgmngr)
                INSTALL_CMD = ['sudo', install_cmd, '-y', 'install']
                DISTRO = (pkgmngr == 'apt-get') and 'ubuntu' or 'redhat'
                if DISTRO == 'ubuntu':
                    subprocess.check_call([install_cmd, '-y', 'update'],
                                          stdout=subprocess.PIPE)
                return
        raise Exception("Coulnd't obtain package manager")


def _installPip():
    global PIP_INSTALLED
    if not PIP_INSTALLED:
        _setInstallCommandAndDistro()
        subprocess.check_call(INSTALL_CMD + ['python-setuptools'], stdout=subprocess.PIPE)
        subprocess.check_call(['sudo', 'easy_install', 'pip'], stdout=subprocess.PIPE)
        PIP_INSTALLED = True


def _installPycryptoDependencies():
    deps = ['gcc', (DISTRO == 'ubuntu') and 'python-dev' or 'python-devel']
    subprocess.check_call(INSTALL_CMD + deps, stdout=subprocess.PIPE)


def _pipInstall(package):
    _installPip()
    subprocess.check_call(['sudo', 'pip', 'install', '-I', package],
                          stdout=subprocess.PIPE)


def _pipInstallParamiko(pycrypto=True):
    if pycrypto:
        _installPycryptoDependencies()

    _pipInstall('paramiko==1.9.0')


def _pipInstallScpclient():
    _pipInstall('scpclient==0.4')


def _pipInstallParamikoScpclinet(pycrypto=False):
    _pipInstallParamiko(pycrypto=False)
    _pipInstallScpclient()


def _installPycryptoParamikoScpclient():
    _setInstallCommandAndDistro()

    _installPip()

    _pipInstallParamiko()
    _pipInstallScpclient()


def _installParamikoScpclient():
    _pipInstallParamikoScpclinet()


def _installScpclient():
    _pipInstallScpclient()


def _paramikoSetup():
    try:
        import Crypto
    except ImportError:
        _installPycryptoParamikoScpclient()
        import Crypto  # noqa
        import paramiko  # noqa
        import scpclient  # noqa
        return
    try:
        import paramiko  # noqa
    except ImportError:
        _installParamikoScpclient()
        import paramiko  # noqa
        import scpclient  # noqa
        return
    try:
        import scpclient  # noqa
    except ImportError:
        _installScpclient()
        import scpclient  # noqa


def _getVerbosity():
    verbosity = ''
    verbosityLevel = os.environ.get('SLIPSTREAM_VERBOSITY_LEVEL', '0')
    try:
        verbosityLevel = int(verbosityLevel)
    except ValueError:
        print '[WARNING]: Verbosity level not an integer. Defaulting to 0.'
    else:
        if verbosityLevel == 1:
            verbosity = '-v'
        elif verbosityLevel == 2:
            verbosity = '-vv'
        elif verbosityLevel >= 3:
            verbosity = '-vvv'

    return verbosity


def getCloudName():
    envCloud = 'SLIPSTREAM_CLOUD'
    try:
        return os.environ[envCloud]
    except KeyError:
        raise RuntimeError('%s environment variable is not defined.' % envCloud)


def _getTargetScriptCommand(targetScript):
    custom_python_bin = os.path.join(os.sep, 'opt', 'python', 'bin')
    print 'Prepending %s to PATH.' % custom_python_bin
    os.putenv('PATH', '%s:%s' % (custom_python_bin, os.environ['PATH']))
    cmd = os.path.join(SLIPSTREAM_CLIENT_HOME, 'sbin', targetScript)
    os.chdir(cmd.rsplit(os.sep, 1)[0])
    if sys.platform == 'win32':
        cmd = 'C:\\Python27\\python ' + cmd
    return cmd + ' ' + _getVerbosity()


def runTargetScript(cmd):
    print 'Calling target script:', cmd
    os.environ['SLIPSTREAM_HOME'] = os.path.join(SLIPSTREAM_CLIENT_HOME, 'sbin')
    subprocess.call(cmd, shell=True)
    sys.stdout.flush()
    sys.stderr.flush()
    sys.exit(0)


def getAndSetupCloudConnector(cloud_name):
    bundle_url = os.environ.get('CLOUDCONNECTOR_BUNDLE_URL')
    if not bundle_url:
        msg = (bundle_url is None) and 'NOT DEFINED' or 'NOT INITIALIZED'
        print '[WARNING]: CLOUDCONNECTOR_BUNDLE_URL is %s for cloud %s' % (msg, cloud_name)
        print '[WARNING]: Skipping downloading of the bundle for %s' % cloud_name
        return

    _deployRemoteTarball(bundle_url,
                         os.path.join(os.sep, 'opt', cloud_name.lower()),
                         cloud_name.lower())


def getAndSetupSlipStream(cloud, orchestration):
    slipstreamTarballUrl = os.environ['SLIPSTREAM_BUNDLE_URL']

    print 'Retrieving the latest version of the SlipStream from:', slipstreamTarballUrl
    _downloadAndExtractTarball(slipstreamTarballUrl, SLIPSTREAM_CLIENT_HOME)
    _setPythonpathSlipStream()
    _setPathSlipStream()
    _buildContextAndConfigSlipStream(cloud, orchestration)
    if orchestration:
        _paramikoSetup()


def createReportsDirectory():
    reportsDir = os.environ.get('SLIPSTREAM_REPORT_DIR',
                                os.path.join(tempfile.gettempdir(),
                                             'slipstream', 'reports'))
    print 'Creating reports directory: %s' % reportsDir
    try:
        os.makedirs(reportsDir)
    except OSError:
        pass


def setupSlipStreamAndCloudConnector(is_orchestration):
    cloud = getCloudName()
    getAndSetupSlipStream(cloud, is_orchestration)
    if is_orchestration:
        getAndSetupCloudConnector(cloud)


def _formatException(exc_info):
    "exc_info - three-element list as returned by sys.exc_info()"
    if int(os.environ.get('SLIPSTREAM_VERBOSITY_LEVEL', '0')) > 0:
        msg_list = traceback.format_exception(*exc_info)
    else:
        msg_list = traceback.format_exception_only(*exc_info[:2])
    return ''.join(msg_list).strip()


def publishFailureToSlipStreamRun(exc_info):
    "exc_info - three-element list as returned by sys.exc_info()"
    AbortPublisher().publish('Bootstrap failed: %s' %
                             _formatException(exc_info))


def main():
    try:
        targetScript = 'slipstream-node-execution'
        if len(sys.argv) > 1:
            targetScript = sys.argv[1]
        is_orchestration = targetScript != 'slipstream-node-execution'

        msg = "=== %s bootstrap script ===" % os.path.basename(targetScript)
        print '{sep}\n{msg}\n{sep}'.format(sep=len(msg) * '=', msg=msg)

        setupSlipStreamAndCloudConnector(is_orchestration)

        createReportsDirectory()

        print 'PYTHONPATH environment variable set to:', os.environ['PYTHONPATH']
        print 'Done bootstrapping!\n'
        sys.stdout.flush()
        sys.stderr.flush()

        cmd = _getTargetScriptCommand(targetScript)
    except:
        publishFailureToSlipStreamRun(sys.exc_info())
        raise

    runTargetScript(cmd)


class AbortPublisher(object):
    def __init__(self):
        self._setup_connection()

    def _setup_connection(self):
        import httplib
        scheme, hostname, port = self._get_service_url_in_parts()
        if scheme == 'https':
            self.c = httplib.HTTPSConnection(hostname, port)
        else:
            self.c = httplib.HTTPConnection(hostname, port)

    def _get_service_url_in_parts(self):
        from urlparse import urlsplit
        url_split = urlsplit(os.environ['SLIPSTREAM_SERVICEURL'])
        return url_split.scheme, url_split.hostname, url_split.port

    def publish(self, message):
        self._process_response(self._publish(message))

    def _publish(self, message):
        try:
            self.c.request('PUT', self._get_request_url(),
                           body=message, headers=self._get_headers())
            return self.c.getresponse()
        finally:
            self.c.close()

    def _get_request_url(self):
        return '/run/%s/ss:abort' % os.environ['SLIPSTREAM_DIID']

    def _get_headers(self):
        return {'user-agent': 'slipstream-bootstrap',
                'accept': 'application/xml',
                'content-type': 'text/plain',
                'cookie': os.environ['SLIPSTREAM_COOKIE'].strip('"')}

    def _process_response(self, response):
        uri = '%s://%s:%s%s' % (self._get_service_url_in_parts()[0],
                                self.c.host, str(self.c.port),
                                self._get_request_url())
        if response.status != 200:
            print 'Failed to publish abort message to %s' % uri
            print response.status, response.reason
            print response.read()
        else:
            print 'Published abort message to %s' % uri

if __name__ == "__main__":
    try:
        main()
    except Exception, e:
        fullFilePath = tempfile.gettempdir() + os.sep + 'slipstream.bootstrap.error'
        file(fullFilePath, 'w').write(str(e))
        raise

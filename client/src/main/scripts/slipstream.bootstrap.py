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
import getpass
import time
import platform
import re

SLIPSTREAM_HOME = os.path.join(os.sep, 'opt', 'slipstream')
SLIPSTREAM_CLIENT_HOME = os.path.join(SLIPSTREAM_HOME, 'client')
SLIPSTREAM_CLIENT_SETUP_DONE_LOCK = os.path.join(SLIPSTREAM_CLIENT_HOME, 'setup.done.lock')

MACHINE_EXECUTOR_NAMES = ['node', 'orchestrator']

INSTALL_CMD = None
DISTRO = None
PIP_INSTALLED = False
RedHat_ver_min_incl_max_excl = ((5,), (7,))
Ubuntu_ver_min_incl_max_excl = ((10,), (14,))
INITD_BASED_DISTROS = dict([('CentOS', RedHat_ver_min_incl_max_excl),
                            ('CentOS Linux', RedHat_ver_min_incl_max_excl),
                            ('RedHat', RedHat_ver_min_incl_max_excl),
                            ('Ubuntu', Ubuntu_ver_min_incl_max_excl)])
RedHat_ver_min_incl_max_excl = ((7,), (8,))
Ubuntu_ver_min_incl_max_excl = ((14,), (15,))
SYSTEMD_BASED_DISTROS = dict([('CentOS', RedHat_ver_min_incl_max_excl),
                            ('CentOS Linux', RedHat_ver_min_incl_max_excl),
                            ('RedHat', RedHat_ver_min_incl_max_excl),
                            ('Ubuntu', Ubuntu_ver_min_incl_max_excl)])

def _versiontuple(v):
    return tuple(map(int, (v.split("."))))


def version_in_range(ver, vrange):
    """Checks if the provided version is in the defined range.
    :param ver: version number to compare
    :type ver: str
    :param vrange: two-tuple with version range ((min included,), (max excluded,)).
    :type vrange: tuple
    """
    return vrange[0] <= _versiontuple(ver) < vrange[1]


class HTTPSConnection(httplib.HTTPSConnection):
    def connect(self):
        """Connect to a host on a given (SSL) port.

        Switching SSL protocol from TLSv1 to SSLv23 as last resort
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


def _set_PYTHONPATH_to_ss():
    ss_lib = os.path.join(SLIPSTREAM_CLIENT_HOME, 'lib')
    __pythonpathPrepend(ss_lib)
    sys.path.append(ss_lib)


def _set_PATH_to_ss():
    for p in ['bin', 'sbin']:
        __pathPrepend(os.path.join(SLIPSTREAM_CLIENT_HOME, p))


def _persist_ss_context_and_config(cloud, orchestration):
    _persist_ss_context()
    _persist_ss_config(cloud, orchestration)


def _persist_ss_context():
    slipstream_context = """[contextualization]
diid = %s
username = %s
cookie = %s
serviceurl = %s
node_instance_name = %s
""" % (os.environ['SLIPSTREAM_DIID'],
       os.environ['SLIPSTREAM_USERNAME'],
       os.environ['SLIPSTREAM_COOKIE'].strip('"'),
       os.environ['SLIPSTREAM_SERVICEURL'],
       os.environ['SLIPSTREAM_NODE_INSTANCE_NAME'])
    _write_to_ss_client_bin('slipstream.context', slipstream_context)


def _persist_ss_config(cloud, orchestration):
    cloud_connector = os.environ.get('CLOUDCONNECTOR_PYTHON_MODULENAME', '')
    # cloud connector module name is only required for orchestration
    if orchestration and not cloud_connector:
        raise RuntimeError("Failed to find connector module name for cloud: %s" % cloud)

    client_config = """[System]
cloudconnector = %s
#storageconnector = slipstream.connectors.LocalCloudStorageConnector
contextualizationconnector = slipstream.connectors.LocalContextualizer
""" % cloud_connector
    _write_to_ss_client_bin('slipstream.client.conf', client_config)


def _write_to_ss_client_bin(fname, content):
    for _dir in ['bin', 'sbin']:
        client_config_file = os.path.join(SLIPSTREAM_CLIENT_HOME, _dir, fname)
        file(client_config_file, 'w').write(content)


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

def _setup_manual_env():
    print "Creating local environment variable script for manual troubleshooting"
    dot_slipstream = '.slipstream'
    slipstream_setenv = 'slipstream.setenv'
    try:
        home = os.path.expanduser("~")
        os.makedirs(os.path.join(home, dot_slipstream))
    except OSError:
        pass
    setenv_file_source = os.path.join(SLIPSTREAM_CLIENT_HOME, 'sbin', slipstream_setenv)
    setenv_file_destination = os.path.join(home, dot_slipstream)
    setenv_file_destination_in_tmp = os.path.join(os.sep, 'tmp', slipstream_setenv)
    try:
        shutil.copyfile(setenv_file_source, setenv_file_destination)
    except IOError, ex:
        pass
    try:
        shutil.copyfile(setenv_file_source, setenv_file_destination_in_tmp)
    except IOError, ex:
        pass

def _deployRemoteTarball(url, extract_to, name):
    print 'Retrieving %s library from %s' % (name, url)
    _downloadAndExtractTarball(url, extract_to)
    __pythonpathPrepend(extract_to)

def _is_root_or_administrator():
    user = getpass.getuser()
    if user == None:
        return False
    else:
        user = user.lower()
    return user == 'root' or user == 'administrator'

def _add_sudo_if_needed(cmd):
    if not _is_root_or_administrator():
        cmd.insert(0, 'sudo')
    return cmd

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
                INSTALL_CMD = _add_sudo_if_needed([install_cmd, '-y', 'install'])
                DISTRO = (pkgmngr == 'apt-get') and 'ubuntu' or 'redhat'
                if DISTRO == 'ubuntu':
                    subprocess.check_call([install_cmd, '-y', 'update'],
                                          stdout=subprocess.PIPE)
                return
        raise Exception("Coulnd't obtain package manager")


def _installPip():
    global PIP_INSTALLED, INSTALL_CMD
    if not PIP_INSTALLED:
        _setInstallCommandAndDistro()
        subprocess.check_call(INSTALL_CMD + ['python-setuptools'], stdout=subprocess.PIPE)
        subprocess.check_call(_add_sudo_if_needed(['easy_install', 'pip']), stdout=subprocess.PIPE)
        PIP_INSTALLED = True

def _installPycryptoDependencies():
    deps = ['gcc', (DISTRO == 'ubuntu') and 'python-dev' or 'python-devel', (DISTRO == 'ubuntu') and 'libgmp3-dev' or 'gmp-devel']
    subprocess.check_call(INSTALL_CMD + deps, stdout=subprocess.PIPE)


def _pipInstall(package):
    _installPip()
    subprocess.check_call(_add_sudo_if_needed(['pip', 'install', '-I', package]),
                          stdout=subprocess.PIPE)


def _pipInstallParamiko(pycrypto=True):
    if pycrypto:
        _installPycryptoDependencies()

    _pipInstall('paramiko==1.15.3')


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
        from Crypto import Random
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


def _get_verbosity():
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


def get_cloud_name():
    envCloud = 'SLIPSTREAM_CLOUD'
    try:
        return os.environ[envCloud]
    except KeyError:
        raise RuntimeError('%s environment variable is not defined.' % envCloud)


def get_machine_executor_command(executor_name):
    try:
        _create_executor_config(executor_name)
        if _system_supports_initd():
            return _setup_and_get_initd_service_start_command(executor_name)
        elif _system_supports_systemd():
            return _setup_and_get_systemd_service_start_command(executor_name)
    except Exception as ex:
        print 'Failed to setup and get service start command for %s executor: %s' % (executor_name, str(ex))
        print 'Falling back to direct startup of %s executor.' % executor_name
        return _get_machine_executor_direct_startup_command(executor_name)
    return _get_machine_executor_direct_startup_command(executor_name)


def _configure_initd_service(executor_name):
    """
    :param executor_name: name of the executor (node or orchestrator)
    :return: init.d service name
    """

    service_name = _add_executor_to_initd(executor_name)

    return service_name


def _add_executor_to_initd(executor_name):
    service_name = "slipstream-%s" % executor_name
    dst = '/etc/init.d/' + service_name
    if not os.path.exists(dst):
        distro = _is_ubuntu() and 'ubuntu' or 'redhat'
        os.symlink(SLIPSTREAM_CLIENT_HOME + '/etc/' + service_name + '-' + distro, dst)

    if _is_ubuntu():
        cmd = 'update-rc.d %s defaults' % service_name
    else:
        cmd = 'chkconfig --add %s' % service_name
    commands.getstatusoutput(cmd)

    return service_name


def _configure_systemd_service(executor_name):
    """
    :param executor_name: name of the executor (node or orchestrator)
    :return: systemd service name
    """

    service_name = _add_executor_to_systemd(executor_name)

    return service_name


def _add_executor_to_systemd(executor_name):
    sname = 'slipstream-%s.service' % executor_name

    src = '/opt/slipstream/client/etc/%s' % sname
    dst = '/etc/systemd/system/%s' % sname

    try: os.unlink(dst)
    except: pass
    os.symlink(src, dst)

    commands.getstatusoutput('systemctl daemon-reload')

    return sname


def _create_executor_config(executor_name):
    conf = {}
    paths = ['/usr/local/sbin', '/usr/local/bin', '/usr/sbin', '/usr/bin', '/sbin', '/bin']
    paths.append(os.path.join(SLIPSTREAM_CLIENT_HOME, 'bin'))
    paths.append(os.path.join(SLIPSTREAM_CLIENT_HOME, 'sbin'))
    conf['PATH'] = os.pathsep.join(paths)
    conf['PYTHONPATH'] = os.path.join(SLIPSTREAM_CLIENT_HOME, 'lib')
    conf['DAEMON_ARGS'] = _get_verbosity()
    conf['SLIPSTREAM_CONNECTOR_INSTANCE'] = os.environ.get('SLIPSTREAM_CONNECTOR_INSTANCE')
    if executor_name == 'orchestrator':
        cloud_name = os.environ['SLIPSTREAM_CLOUD']
        pypath_prep = conf.get('PYTHONPATH', '') and (conf.get('PYTHONPATH', '') + os.pathsep) or ''
        conf['PYTHONPATH'] =  pypath_prep + os.path.join(os.sep, 'opt', cloud_name.lower())
        env_matcher = re.compile('SLIPSTREAM_')
        for var, val in os.environ.items():
            if env_matcher.match(var) and var != 'SLIPSTREAM_NODE_INSTANCE_NAME':
                #if re.search(' ', val) and not (val.startswith('"') and val.endswith('"')):
                if re.search(' ', val) and not 'SLIPSTREAM_COOKIE':
                    val = '"%s"' % val
                conf[var] = val

    _write_executor_config(executor_name, conf)


def _write_executor_config(executor_name, conf):
    initd = _system_supports_initd()

    def _write(fh, _str):
        fh.write((initd and 'export ' or '') + _str)

    defaults_file = '/etc/default/slipstream-%s' % executor_name
    with open(defaults_file, 'w') as fh:
        for k, v in conf.items():
            _write(fh, '%s=%s\n' % (k, v))


def _setup_and_get_initd_service_start_command(executor_name):
    service_name = _configure_initd_service(executor_name)
    return "service %s start" % service_name


def _setup_and_get_systemd_service_start_command(executor_name):
    service_name = _configure_systemd_service(executor_name)
    return 'systemctl start %s' % service_name


def _get_linux_distribution():
    return platform.linux_distribution()


def _system_supports_initd():
    return _system_supports_init_process(INITD_BASED_DISTROS)


def _system_supports_systemd():
    return _system_supports_init_process(SYSTEMD_BASED_DISTROS)


def _system_supports_init_process(distros):
    """distros - dict {'distro name': (ver_min_incl, ver_max_excl), }
    """
    if not _is_linux():
        return False
    distname, version, _id = _get_linux_distribution()
    if distname not in distros.keys():
        return False
    else:
        initd_dist_version_range = distros[distname]
        return version_in_range(version, initd_dist_version_range)


def _is_ubuntu():
    distname, _, _ = platform.linux_distribution()
    return distname.lower().startswith('ubuntu')


def _is_linux():
    return sys.platform.startswith('linux')


def _get_machine_executor_direct_startup_command(executor_name):
    custom_python_bin = os.path.join(os.sep, 'opt', 'python', 'bin')
    print 'Prepending %s to PATH.' % custom_python_bin
    os.putenv('PATH', '%s:%s' % (custom_python_bin, os.environ['PATH']))
    cmd = os.path.join(SLIPSTREAM_CLIENT_HOME, 'sbin', 'slipstream-%s' % executor_name)
    os.chdir(cmd.rsplit(os.sep, 1)[0])
    if sys.platform == 'win32':
        cmd = 'C:\\Python27\\python ' + cmd
    return cmd + ' ' + _get_verbosity()


def start_machine_executor(cmd):
    print 'Calling target script:', cmd
    os.environ['SLIPSTREAM_HOME'] = os.path.join(SLIPSTREAM_CLIENT_HOME, 'sbin')
    subprocess.call(cmd, shell=True)
    sys.stdout.flush()
    sys.stderr.flush()
    sys.exit(0)


def get_and_setup_cloud_connector(cloud_name):
    bundle_url = os.environ.get('CLOUDCONNECTOR_BUNDLE_URL')
    if not bundle_url:
        msg = (bundle_url is None) and 'NOT DEFINED' or 'NOT INITIALIZED'
        print '[WARNING]: CLOUDCONNECTOR_BUNDLE_URL is %s for cloud %s' % (msg, cloud_name)
        print '[WARNING]: Skipping downloading of the bundle for %s' % cloud_name
        return

    _deployRemoteTarball(bundle_url,
                         os.path.join(os.sep, 'opt', cloud_name.lower()),
                         cloud_name.lower())


def _set_env_paths_to_ss():
    _set_PYTHONPATH_to_ss()
    _set_PATH_to_ss()


def get_and_setup_ss(cloud, orchestration):
    _set_env_paths_to_ss()

    if os.path.exists(SLIPSTREAM_CLIENT_SETUP_DONE_LOCK):
        print 'NOTE: Skipping download and configuration of SlipStream machine executor.'
        print 'NOTE: SlipStream machine executor was already configured on the host on %s' % \
              open(SLIPSTREAM_CLIENT_SETUP_DONE_LOCK, 'r').read()
        return

    ss_tarball_url = os.environ['SLIPSTREAM_BUNDLE_URL']
    print 'Retrieving the latest version of the SlipStream from:', ss_tarball_url
    _downloadAndExtractTarball(ss_tarball_url, SLIPSTREAM_CLIENT_HOME)
    _setup_manual_env()
    _persist_ss_context_and_config(cloud, orchestration)
    if orchestration:
        _paramikoSetup()
    _set_setup_done_lock()


def _set_setup_done_lock():
    with open(SLIPSTREAM_CLIENT_SETUP_DONE_LOCK, 'w') as fh:
        fh.write(_to_time_in_iso8601(time.time()))


def _to_time_in_iso8601(_time):
    """Convert int or float to time in iso8601 format."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(_time))


def setup_ss_and_cloud_connector(is_orchestration):
    cloud = get_cloud_name()
    get_and_setup_ss(cloud, is_orchestration)
    if is_orchestration:
        get_and_setup_cloud_connector(cloud)


def _formatException(exc_info):
    "exc_info - three-element list as returned by sys.exc_info()"
    if int(os.environ.get('SLIPSTREAM_VERBOSITY_LEVEL', '0')) > 0:
        msg_list = traceback.format_exception(*exc_info)
    else:
        msg_list = traceback.format_exception_only(*exc_info[:2])
    return ''.join(msg_list).strip()


def publish_failure_to_ss_run(exc_info):
    "exc_info - three-element list as returned by sys.exc_info()"
    AbortPublisher().publish('Bootstrap failed: %s' %
                             _formatException(exc_info))


def main():
    try:
        machine_executor = 'node'
        if len(sys.argv) > 1:
            machine_executor = sys.argv[1]
        is_orchestration = machine_executor != 'node'

        msg = "=== %s bootstrap ===" % machine_executor
        print '{sep}\n{msg}\n{sep}'.format(sep=len(msg) * '=', msg=msg)

        setup_ss_and_cloud_connector(is_orchestration)

        print 'PYTHONPATH environment variable set to:', os.environ['PYTHONPATH']
        print 'Done bootstrapping!\n'

        cmd = get_machine_executor_command(machine_executor)
        sys.stdout.flush()
        sys.stderr.flush()
    except:
        publish_failure_to_ss_run(sys.exc_info())
        raise

    start_machine_executor(cmd)


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

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
PIP_UPGRADED = False
PIP_CERTLOC = None

PARAMIKO_VER = '1.15.3'
SCPCLIENT_VER = '0.4'

"""
Matrix showing support of different init implementations by different versions of RedHat and Ubuntu.

                  systemd  | init.d   | upstart
 RedHat <= 6         NO    |   YES    |   NO
 RedHat >= 7        YES    |   YES*   |   NO
 Ubuntu <= 14.04     NO    |   YES    |  YES
 Ubuntu == 14.10    YES**  |   YES    |  YES
 Ubuntu >= 15.x     YES    |   YES*   |   ?
 SUSE   <= 11        NO    |   YES*   |   ?
 SUSE   >= 12       YES    |   YES*   |   ?

 *  - via redirect to systemd, provided LSB info in init.d file is correct for systemd;
 ** - with 'systemd-sysv' package replaces upstart completely or with 'systemd' package
      runs along with upstart;
 ? - I don't know (konstan).
"""
INITD_RedHat_ver_min_incl_max_excl = ((5,), (7,))
INITD_Ubuntu_ver_min_incl_max_excl = ((10,), (15,))
INITD_SUSE_ver_min_incl_max_excl = ((11,), (12,))
INITD_BASED_DISTROS = dict([('CentOS', INITD_RedHat_ver_min_incl_max_excl),
                            ('CentOS Linux', INITD_RedHat_ver_min_incl_max_excl),
                            ('RedHat', INITD_RedHat_ver_min_incl_max_excl),
                            ('openSUSE', INITD_SUSE_ver_min_incl_max_excl),
                            ('SUSE Linux Enterprise Server', INITD_SUSE_ver_min_incl_max_excl),
                            ('SUSE Linux Enterprise Desktop', INITD_SUSE_ver_min_incl_max_excl),
                            ('Ubuntu', INITD_Ubuntu_ver_min_incl_max_excl)])
SYSTEMD_RedHat_ver_min_incl_max_excl = ((7,), (8,))
SYSTEMD_Ubuntu_ver_min_incl_max_excl = ((15,), (16,))
SYSTEMD_SUSE_ver_min_incl_max_excl = ((12,), (13,))
SYSTEMD_BASED_DISTROS = dict([('CentOS', SYSTEMD_RedHat_ver_min_incl_max_excl),
                              ('CentOS Linux', SYSTEMD_RedHat_ver_min_incl_max_excl),
                              ('RedHat', SYSTEMD_RedHat_ver_min_incl_max_excl),
                              ('openSUSE', SYSTEMD_SUSE_ver_min_incl_max_excl),
                              ('SUSE Linux Enterprise Server', SYSTEMD_SUSE_ver_min_incl_max_excl),
                              ('SUSE Linux Enterprise Desktop', SYSTEMD_SUSE_ver_min_incl_max_excl),
                              ('Ubuntu', SYSTEMD_Ubuntu_ver_min_incl_max_excl)])


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


def info(*args):
    print ' '.join(map(str, args))


def error(*args):
    print "ERROR:", ' '.join(map(str, args))


def warning(*args):
    print "WARNING:", ' '.join(map(str, args))


def _get_verbosity_level():
    level = 0
    try:
        level = int(os.environ.get('SLIPSTREAM_VERBOSITY_LEVEL', level))
    except ValueError:
        warning('Provided verbosity level is not an integer. Defaulting to %s.' % level)
    return level


def _get_verbosity_arg():
    verbosity = ''
    level = _get_verbosity_level()
    if level in [0, 1]:
        verbosity = '-v'
    elif level == 2:
        verbosity = '-vv'
    elif level >= 3:
        verbosity = '-vvv'

    return verbosity


VERBOSITY_LEVEL = _get_verbosity_level()


def debug(*args):
    if VERBOSITY_LEVEL >= 2:
        print "DEBUG:", ' '.join(map(str, args))


def _get_rc_output(cmd):
    status, output = commands.getstatusoutput(cmd)
    return os.WEXITSTATUS(status), output


def _find_executable(name):
    rc, exe = _get_rc_output('which ' + name)
    if rc == 0:
        return exe.strip()
    else:
        return ''


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
    __pythonpath_prepend(ss_lib)
    sys.path.append(ss_lib)


def _set_PATH_to_ss():
    for p in ['bin', 'sbin']:
        __path_prepend(os.path.join(SLIPSTREAM_CLIENT_HOME, p))


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


def __pythonpath_prepend(path):
    __env_path_prepend('PYTHONPATH', path)


def __path_prepend(path):
    __env_path_prepend('PATH', path)


def __env_path_prepend(envvar, path):
    pathList = os.environ.get(envvar, '').split(os.pathsep)
    pathList.insert(0, path)
    os.environ[envvar] = os.pathsep.join(pathList)


def _download(src_url, dst_file):
    try:
        src_fh = urllib2.urlopen(src_url)
    except Exception as ex:
        error('Failed contacting:', src_url, 'with error:"', ex, '"retrying...')
        src_fh = urllib2.urlopen(src_url)

    dst_fh = open(dst_file, 'wb')
    while True:
        data = src_fh.read()
        if not data:
            break
        dst_fh.write(data)
    src_fh.close()
    dst_fh.close()

    return dst_file


def _download_and_extract_tarball(tarball_url, target_dir):
    try:
        shutil.rmtree(target_dir, ignore_errors=True)
        os.makedirs(target_dir)
    except OSError:
        pass

    local_tarball = _download(tarball_url,
                              os.path.join(target_dir, os.path.basename(tarball_url)))

    info('Expanding tarball:', local_tarball)
    tarfile.open(local_tarball, 'r:gz').extractall(target_dir)


def _setup_manual_env():
    info("Creating local environment variable script for manual troubleshooting.")
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
    except IOError as ex:
        pass
    try:
        shutil.copyfile(setenv_file_source, setenv_file_destination_in_tmp)
    except IOError as ex:
        pass


def _deploy_remote_tarball(url, extract_to, name):
    info('Retrieving', name, 'library from:', url)
    _download_and_extract_tarball(url, extract_to)
    __pythonpath_prepend(extract_to)


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


def _check_call(cmd):
    subprocess.check_call(_add_sudo_if_needed(cmd), stdout=subprocess.PIPE)


def _set_install_command_and_distro():
    global INSTALL_CMD, DISTRO
    pkgmngr_distro = {'apt-get': 'ubuntu',
                      'yum': 'redhat',
                      'zypper': 'suse'}

    if not INSTALL_CMD or not DISTRO:
        for pkgmngr in pkgmngr_distro.keys():
            try:
                _check_call([pkgmngr, '-h'])
            except (subprocess.CalledProcessError, OSError):
                pass
            else:
                # TODO: on Ubuntu 10.04 there is no subprocess.check_output()!!!
                install_cmd = commands.getoutput('which %s' % pkgmngr)
                INSTALL_CMD = [install_cmd, 'install', '-y']
                DISTRO = pkgmngr_distro[pkgmngr]
                if DISTRO == 'ubuntu':
                    _check_call([install_cmd, '-y', 'update'])
                return
        raise Exception("Couldn't obtain package manager.")


def _pip_run_cmd(cmd):
    """cmd - list of strings, e.g. ['install', '-I', 'my-package']
    """
    global PIP_CERTLOC
    _cmd = ['pip'] + cmd
    try:
        _check_call(_cmd)
    except subprocess.CalledProcessError:
        # May need this on some old distros.
        # https://mkcert.org/generate/
        if not PIP_CERTLOC:
            PIP_CERTLOC = _download('https://mkcert.org/generate/', tempfile.gettempdir() + os.sep + 'pip-certs.pem')
            # NB! The below command is preferred, but may return an expired cert if pip is too old.
            # PIP_CERTLOC = commands.getoutput('python -m pip._vendor.requests.certs')
        _check_call(_cmd + ['--cert', PIP_CERTLOC])


def _upgrade_pip():
    global PIP_UPGRADED
    if not PIP_UPGRADED:
        # NB! Fail on reinstall to get certs to be able to successfully upgrade.
        #     Otherwise, w/o -I the upgrade of pip itself doesn't fail.
        _pip_run_cmd(['install', '--upgrade', '-I', 'pip'])
        _pip_run_cmd(['install', '--upgrade', 'pip'])
        PIP_UPGRADED = True


def _install_pip():
    global PIP_INSTALLED
    if not PIP_INSTALLED:
        _set_install_command_and_distro()
        _check_call(INSTALL_CMD + ['python-setuptools'])
        _check_call(_add_sudo_if_needed(['easy_install', 'pip']))
        __path_prepend('/usr/local/sbin')
        __path_prepend('/usr/local/bin')
        PIP_INSTALLED = True


def _with_pip(fn):
    def wrapped(*args, **kwargs):
        _install_pip()
        _upgrade_pip()
        fn(*args, **kwargs)

    return wrapped


@_with_pip
def _pip_install(package):
    _pip_run_cmd(['install', '-I', package])


def _install_pycrypto_dependencies():
    deps = ['gcc',
            (DISTRO == 'ubuntu') and 'python-dev' or 'python-devel',
            (DISTRO == 'ubuntu') and 'libgmp3-dev' or 'gmp-devel']
    _check_call(INSTALL_CMD + deps)


def _pip_install_paramiko(pycrypto=True):
    if pycrypto:
        _install_pycrypto_dependencies()

    _pip_install('paramiko==' + PARAMIKO_VER)


def _pip_install_scpclient():
    _pip_install('scpclient==' + SCPCLIENT_VER)


def _pip_install_paramiko_scpclinet(pycrypto=False):
    _pip_install_paramiko(pycrypto=False)
    _pip_install_scpclient()


def _install_pycrypto_paramiko_scpclient():
    _set_install_command_and_distro()

    _pip_install_paramiko()
    _pip_install_scpclient()


def _install_paramiko_scpclient():
    _pip_install_paramiko_scpclinet()


def _install_scpclient():
    _pip_install_scpclient()


def _paramiko_setup():
    try:
        from Crypto import Random
    except ImportError:
        _install_pycrypto_paramiko_scpclient()
        import Crypto  # noqa
        import paramiko  # noqa
        import scpclient  # noqa
        return
    try:
        import paramiko  # noqa
    except ImportError:
        _install_paramiko_scpclient()
        import paramiko  # noqa
        import scpclient  # noqa
        return
    try:
        import scpclient  # noqa
    except ImportError:
        _install_scpclient()
        import scpclient  # noqa


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
            debug("System supports init.d.")
            return _setup_and_get_initd_service_start_command(executor_name)
        elif _system_supports_systemd():
            debug("System supports systemd.")
            return _setup_and_get_systemd_service_start_command(executor_name)
    except Exception as ex:
        warning('Failed to setup and get service start command for %s executor: %s' % (executor_name, str(ex)))
        warning('Falling back to direct startup of %s executor.' % executor_name)
        return _get_machine_executor_direct_startup_command(executor_name)
    warning('Failed to determine support for init.d or systemd.')
    warning('Falling back to direct startup of %s executor.' % executor_name)
    return _get_machine_executor_direct_startup_command(executor_name)


def _configure_initd_service(executor_name):
    """
    :param executor_name: name of the executor (node or orchestrator)
    :return: init.d service name
    """

    service_name = _add_executor_to_initd(executor_name)

    return service_name


def _chkconfig_cmd(service_name):
    cli = _find_executable('chkconfig')
    # /sbin may not be in PATH on SLES 11.
    if not cli:
        cli = '/sbin/chkconfig'
    return cli + ' --add ' + service_name


def _add_executor_to_initd(executor_name):
    service_name = "slipstream-%s" % executor_name
    dst = '/etc/init.d/' + service_name
    if not os.path.exists(dst):
        os.symlink(SLIPSTREAM_CLIENT_HOME + '/etc/' + service_name, dst)

    if _is_ubuntu():
        cmd = 'update-rc.d %s defaults' % service_name
    else:
        cmd = _chkconfig_cmd(service_name)

    rc, output = _get_rc_output(cmd)
    if rc != 0:
        raise Exception('Failed registering machine executor with initd: %s' % output)

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

    try:
        os.unlink(dst)
    except:
        pass
    shutil.copy(src, dst)
    cmds = ['systemctl enable %s' % sname, 'systemctl daemon-reload']
    for cmd in cmds:
        rc, output = _get_rc_output(cmd)
        if rc != 0:
            raise Exception('Failed registering machine executor with systemd: %s' % output)

    return sname


def _create_executor_config(executor_name):
    conf = {}
    paths = ['/usr/local/sbin', '/usr/local/bin', '/usr/sbin', '/usr/bin', '/sbin', '/bin']
    paths.append(os.path.join(SLIPSTREAM_CLIENT_HOME, 'bin'))
    paths.append(os.path.join(SLIPSTREAM_CLIENT_HOME, 'sbin'))
    conf['PATH'] = os.pathsep.join(paths)
    conf['PYTHONPATH'] = os.path.join(SLIPSTREAM_CLIENT_HOME, 'lib')
    conf['DAEMON_ARGS'] = _get_verbosity_arg()
    conf['SLIPSTREAM_CONNECTOR_INSTANCE'] = os.environ.get('SLIPSTREAM_CONNECTOR_INSTANCE')
    if executor_name == 'orchestrator':
        cloud_name = os.environ['SLIPSTREAM_CLOUD']
        pypath_prep = conf.get('PYTHONPATH') + os.pathsep if conf.get('PYTHONPATH', '') else ''
        conf['PYTHONPATH'] = pypath_prep + os.path.join(os.sep, 'opt', cloud_name.lower())
        env_matcher = re.compile('SLIPSTREAM_')
        for var, val in os.environ.items():
            if env_matcher.match(var) and var != 'SLIPSTREAM_NODE_INSTANCE_NAME':
                if re.search(' ', val) and not (val.startswith('"') and val.endswith('"')):
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


def _service_cmd(service_name):
    cli = _find_executable('service')
    # /sbin may not be in PATH on SLES 11.
    if not cli:
        cli = '/sbin/service'
    return cli + (' %s start' % service_name)


def _setup_and_get_initd_service_start_command(executor_name):
    service_name = _configure_initd_service(executor_name)
    return _service_cmd(service_name)


def _setup_and_get_systemd_service_start_command(executor_name):
    service_name = _configure_systemd_service(executor_name)
    return 'systemctl start %s' % service_name


def _get_linux_distribution():
    distname, version, _id = platform.linux_distribution()
    return distname.strip(), version, _id


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


def _is_suse():
    distname, _, _ = platform.linux_distribution()
    return 'SUSE' in distname


def _is_linux():
    return sys.platform.startswith('linux')


def _get_machine_executor_direct_startup_command(executor_name):
    custom_python_bin = os.path.join(os.sep, 'opt', 'python', 'bin')
    info('Prepending %s to PATH.' % custom_python_bin)
    os.putenv('PATH', '%s:%s' % (custom_python_bin, os.environ['PATH']))
    cmd = os.path.join(SLIPSTREAM_CLIENT_HOME, 'sbin', 'slipstream-%s' % executor_name)
    os.chdir(cmd.rsplit(os.sep, 1)[0])
    if sys.platform == 'win32':
        cmd = 'C:\\Python27\\python ' + cmd
    return cmd + ' ' + _get_verbosity_arg()


def start_machine_executor(cmd):
    info('Calling target script:', cmd)
    os.environ['SLIPSTREAM_HOME'] = os.path.join(SLIPSTREAM_CLIENT_HOME, 'sbin')
    rc = subprocess.call(cmd, shell=True)
    sys.stdout.flush()
    sys.stderr.flush()
    if rc != 0:
        raise Exception('Failed starting machine executor: %s. Return code %s.' % (cmd, rc))


def get_and_setup_cloud_connector(cloud_name):
    bundle_url = os.environ.get('CLOUDCONNECTOR_BUNDLE_URL')
    if not bundle_url:
        msg = (bundle_url is None) and 'NOT DEFINED' or 'NOT INITIALIZED'
        warning('CLOUDCONNECTOR_BUNDLE_URL is %s for cloud %s' % (msg, cloud_name))
        warning('Skipping downloading of the bundle for %s' % cloud_name)
        return

    _deploy_remote_tarball(bundle_url,
                           os.path.join(os.sep, 'opt', cloud_name.lower()),
                           cloud_name.lower())


def _set_env_paths_to_ss():
    _set_PYTHONPATH_to_ss()
    _set_PATH_to_ss()


def get_and_setup_ss(cloud, orchestration):
    _set_env_paths_to_ss()

    if os.path.exists(SLIPSTREAM_CLIENT_SETUP_DONE_LOCK):
        warning('Skipping download and configuration of SlipStream machine executor.')
        warning('SlipStream machine executor was already configured on the host on %s' % \
                open(SLIPSTREAM_CLIENT_SETUP_DONE_LOCK, 'r').read())
        return

    ss_tarball_url = os.environ['SLIPSTREAM_BUNDLE_URL']
    info('Retrieving the latest version of the SlipStream from:', ss_tarball_url)
    _download_and_extract_tarball(ss_tarball_url, SLIPSTREAM_CLIENT_HOME)
    _setup_manual_env()
    _persist_ss_context_and_config(cloud, orchestration)
    if orchestration:
        _paramiko_setup()
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
        info('{sep}\n{msg}\n{sep}'.format(sep=len(msg) * '=', msg=msg))

        setup_ss_and_cloud_connector(is_orchestration)

        info('PYTHONPATH environment variable set to:', os.environ['PYTHONPATH'])
        info('Done bootstrapping!\n')

        cmd = get_machine_executor_command(machine_executor)
        sys.stdout.flush()
        sys.stderr.flush()

        start_machine_executor(cmd)
    except:
        publish_failure_to_ss_run(sys.exc_info())
        raise
    else:
        sys.exit(0)


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
            error('Failed to publish abort message to', uri)
            error(response.status, response.reason)
            error(response.read())
        else:
            print 'Published abort message to %s' % uri


if __name__ == "__main__":
    try:
        main()
    except Exception, e:
        fullFilePath = tempfile.gettempdir() + os.sep + 'slipstream.bootstrap.error'
        file(fullFilePath, 'w').write(str(e))
        raise

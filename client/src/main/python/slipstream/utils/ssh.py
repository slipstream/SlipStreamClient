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

import re
import copy
import errno
import os
import tempfile
import time
from contextlib import closing
import socket
import exceptions

import paramiko
from paramiko import SSHClient
from paramiko.ssh_exception import AuthenticationException
from Crypto.PublicKey import RSA

from slipstream.util import execute, _printDetail
from slipstream.exceptions import Exceptions
from slipstream.utils.pyCryptoPatch import pyCryptoPatch
import scpclient


SSH_PORT = '22'
SSH_EXIT_STATUS_ERROR = 255
SSH_CONNECTION_RETRY_NUMBER = 2
SSH_CONNECTION_RETRY_SLEEP_MAX = 5
CONNECT_TIMEOUT = 10


def generate_ssh_keypair(key_filename):
    try:
        os.remove(key_filename)
        os.remove(key_filename + '.pub')
    except(OSError):
        pass
    ssh_cmd = 'ssh-keygen -f %s -N "" -q' % key_filename
    execute(ssh_cmd, shell=True)


def generate_keypair(bits=2048):
    pyCryptoPatch()
    private = RSA.generate(bits)
    public = private.publickey()
    return private.exportKey(), public.exportSSHKey()  # public.exportKey(format='OpenSSH')


def scp(src, dst, user, host, sshKey=None, password='',
        timeout=CONNECT_TIMEOUT, **kwargs):
    """Uses either SSH CLI or API (paramiko).

    SSH API is used only when 'password' is provided. When 'password' and 'sshKey'
    (path to the SSH private key file) are provided at the same time - the
    password is considered the password for the SSH private key.

    In all other cases SSH CLI is used."""
    if password:
        return _scp_api(src, user, host, dst, password=password,
                        sshKey=sshKey, timeout=timeout)
    else:
        return _scp_cli(src, '%s@%s:%s' % (user, host, dst),
                        sshKey=sshKey, timeout=timeout, **kwargs)


def _scp_api(src, user, host, dst, password='', sshKey=None,
             timeout=CONNECT_TIMEOUT):
    ssh = _ssh_connect_api(host, user, password,
                           sshKey=sshKey, tcp_timeout=timeout)
    with closing(scpclient.Write(ssh.get_transport(), os.path.dirname(dst))) as _scp:
        _scp.send_file(src, os.path.basename(dst))

    return 0, 'success'


def _scp_cli(src, dest, sshKey=None, timeout=CONNECT_TIMEOUT, **kwargs):
    scpCmd = ['scp', '-P', SSH_PORT, '-r', '-o', 'StrictHostKeyChecking=no',
              '-o', 'ConnectTimeout=%i' % timeout]

    if sshKey and os.path.isfile(sshKey):
        scpCmd.append('-i')
        scpCmd.append(sshKey)

    scpCmd.append(src)
    scpCmd.append(dest)

    return execute(scpCmd, **kwargs)


def sshCmd(cmd, host, sshKey=None, user='root', password='',
           timeout=CONNECT_TIMEOUT, **kwargs):
    """Uses either SSH CLI or API (paramiko).

    SSH API is used only when 'password' is provided. When 'password' and 'sshKey'
    (path to the SSH private key file) are provided at the same time - the
    password is considered the password for the SSH private key.

    In all other cases SSH CLI is used."""
    if password:
        return _ssh_execute_api(cmd, host, user, password, sshKey,
                                timeout, **kwargs)
    else:
        return _ssh_execute_cli(cmd, host, user, sshKey,
                                timeout, **kwargs)


def _ssh_connect_api(hostname, username, password, sshKey=None,
                     tcp_timeout=CONNECT_TIMEOUT):
    sshKey = sshKey or None
    ssh = SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=hostname,
                username=username,
                password=password,
                timeout=tcp_timeout,
                key_filename=sshKey)
    return ssh


def _ssh_execute_api(cmd, hostname, username, password, sshKey, tcp_timeout,
                     **kwargs):
    def _ssh_exec_get_stdouterr(ssh, cmd):
        transport = ssh.get_transport()
        channel = transport.open_session()
        # merge stdout and stderr
        channel.get_pty()
        stdout = channel.makefile('rb', -1)
        channel.exec_command(cmd)
        return stdout

    def _ssh_getstatusoutput(ssh, cmd, **kwargs):
        stdout = _ssh_exec_get_stdouterr(ssh, cmd)

        lines = []
        line = stdout.readline()
        if 'withOutput' in kwargs or 'withStderr' in kwargs:
            while line:  # or not stdout.channel.exit_status_ready():
                lines.append(line)
                line = stdout.readline()
        else:
            while line:  # or not stdout.channel.exit_status_ready():
                print line,
                line = stdout.readline()

        exit_status = stdout.channel.recv_exit_status()
        if 'withOutput' in kwargs or 'withStderr' in kwargs:
            output = ''.join(lines)
            return exit_status, output
        else:
            return exit_status

    ssh = _ssh_connect_api(hostname, username, password,
                           sshKey=sshKey, tcp_timeout=tcp_timeout)
    return _ssh_getstatusoutput(ssh, cmd, **kwargs)


def _ssh_execute_cli(cmd, host, user, sshKey, tcp_timeout, **kwargs):
    def _appendToSshCommandFromKwargs(keyword, append):
        if kwargs.get(keyword, False):
            sshCmd.append(append)
        try:
            del kwargs[keyword]
        except:
            pass

    def _removeInvalidExecuteKwargs():
        for keyword in ['verboseLevel', 'verboseThreshold', 'password']:
            try:
                del kwargs[keyword]
            except:
                pass

    sshCmd = ['ssh', '-p', SSH_PORT, '-o', 'ConnectTimeout=%s' % tcp_timeout,
              '-o', 'StrictHostKeyChecking=no']

    if sshKey and os.path.isfile(sshKey):
        sshCmd.append('-i')
        sshCmd.append(sshKey)

    for keyAppend in [('sshVerb', '-v'), ('sshQuiet', '-q'), ('pseudoTTY', '-t -t')]:
        _appendToSshCommandFromKwargs(*keyAppend)

    sshCmd.append('%s@%s' % (user, host))
    sshCmd.append(cmd)

    _removeInvalidExecuteKwargs()

    return execute(sshCmd, **kwargs)


def sshCmdWithOutput(cmd, host, sshKey=None, user='root', password='',
                     timeout=CONNECT_TIMEOUT, **kwargs):
    return sshCmd(cmd, host, sshKey=sshKey,
                  user=user, password=password, timeout=timeout,
                  withOutput=True, **kwargs)


def sshCmdWithStderr(cmd, host, sshKey=None, user='root', password='',
                     timeout=CONNECT_TIMEOUT, **kwargs):
    return sshCmd(cmd, host, sshKey=sshKey,
                  user=user, password=password, timeout=timeout,
                  withStderr=True, **kwargs)


def sshCmdWithOutputVerb(cmd, host, sshKey=None, user='root', password='',
                         timeout=CONNECT_TIMEOUT, **kwargs):
    return sshCmd(cmd, host, sshKey=sshKey,
                  user=user, password=password, timeout=timeout,
                  withOutput=True, sshVerb=True, **kwargs)


class SshFailedToConnect(Exception):
    pass


class SshConnectionRefused(SshFailedToConnect):
    pass


class SshHostUnreachable(SshFailedToConnect):
    pass


class SshConnectionResetByPeer(SshFailedToConnect):
    pass


class SshConnectionTimedOut(SshFailedToConnect):
    pass


class SshServerNameNotKnown(Exception):
    pass


class SshAuthFailed(Exception):
    pass


def waitUntilSshCanConnectOrTimeout(host, timeout, user='root', password='',
                                    sshKey=None, **kwargs):
    """Returns True on success or raises on any unhandled failures.
    """
    kind = password and 'api' or 'cli'
    time_stop = time.time() + timeout
    timeout_connect = 3
    auth_failures = 20

    reason = 'Unknown'
    while (time_stop - time.time()) >= 0:
        kwargs_ = copy.copy(kwargs)
        try:
            print kind
            if True == globals()['_ssh_can_connect_' + kind](host, user,
                                                             sshKey=sshKey, password=password,
                                                             timeout=timeout_connect, **kwargs_):
                return True
        except SshConnectionRefused as ex:
            _printDetail(str(ex), kwargs_)
            reason = 'SshConnectionRefused'
            time.sleep(5)
        except SshHostUnreachable as ex:
            _printDetail(str(ex), kwargs_)
            reason = 'SshHostUnreachable'
            time.sleep(10)
        except SshConnectionResetByPeer as ex:
            _printDetail(str(ex), kwargs_)
            reason = 'SshConnectionResetByPeer'
            time.sleep(5)
        except SshConnectionTimedOut as ex:
            _printDetail(str(ex), kwargs_)
            reason = 'SshConnectionTimedOut'
            timeout_connect *= 2
        except SshServerNameNotKnown as ex:
            _printDetail(str(ex), kwargs_)
            raise
        except SshAuthFailed as ex:
            _printDetail(('%i: ' % auth_failures) + str(ex), kwargs_)
            reason = 'SshAuthFailed'
            if auth_failures <= 0:
                raise
            auth_failures -= 1
            time.sleep(5)
        except SshFailedToConnect as ex:
            reason = 'SshFailedToConnect'
            _printDetail(str(ex), kwargs_)
            time.sleep(5)
        except paramiko.SSHException as ex:
            _printDetail(str(ex), kwargs_)
            reason = 'paramiko.SSHException:', str(ex)
            time.sleep(5)
        except exceptions.EOFError as ex:
            _printDetail(str(ex), kwargs_)
            reason = 'exceptions.EOFError'
            time.sleep(5)

    raise Exceptions.TimeoutException('Failed to connect after %s sec. \nReason: %s'
                                      % (timeout, reason))


def _ssh_can_connect_api(host, user, sshKey=None, password=None, timeout=None,
                         **kwargs):
    try:
        ssh = _ssh_connect_api(host, user, password, sshKey=sshKey,
                               tcp_timeout=timeout)
    except socket.error as ex:
        if ex.errno == errno.ECONNREFUSED:
            raise SshConnectionRefused('Connection refused. %s' % ex)
        elif ex.errno == errno.ENETUNREACH:
            raise SshHostUnreachable('Host unreachable. %s' % ex)
        elif ex.errno == errno.ECONNRESET:
            raise SshConnectionResetByPeer('Connection reset by peer. %s' % ex)
        elif ex.message == 'timed out':
            raise SshConnectionTimedOut('Connection timed out. %s' % ex)
        elif ex.errno == errno.ENOEXEC:
            raise SshServerNameNotKnown(str(ex))
        else:
            raise SshFailedToConnect('Failed to connect: %s' % str(ex))
    except AuthenticationException as ex:
        raise SshAuthFailed(ex)
    else:
        ssh.close()
        return True


def _ssh_can_connect_cli(host, user, sshKey=None, timeout=None, **kwargs):
    rc_output = _ssh_execute_cli('true', host, user, sshKey, timeout,
                                 withOutput=True, **kwargs)
    if isinstance(rc_output, int):
        rc = rc_output
    else:
        rc = rc_output[0]
    if rc == SSH_EXIT_STATUS_ERROR:
        try:
            output = rc_output[1]
        except (IndexError, TypeError):
            output = ''
        if output:
            if re.search('Could not resolve hostname', output):
                raise SshServerNameNotKnown(output)
            elif re.search('Permission denied', output):
                raise SshAuthFailed(output)
        raise SshFailedToConnect('Failed to connect: %s' % output)
    return (rc == 0) and True or False


def remoteRunScript(user, host, script, sshKey=None, password='', nohup=False):
    fd, scriptFile = tempfile.mkstemp()
    try:
        os.write(fd, script)
        os.close(fd)
        os.chmod(scriptFile, 0755)
        dstScriptFile = '/tmp/%s' % os.path.basename(scriptFile)
        retry_count = 3
        while True:
            rc, stderr = scp(scriptFile, dstScriptFile, user, host,
                             sshKey=sshKey, password=password, withStderr=True)
            if rc != 0:
                if retry_count <= 0:
                    raise Exceptions.ExecutionException("An error occurred while uploading "
                                                        "script to %s: %s" % (host, stderr))
                else:
                    time.sleep(5)
                    retry_count -= 1
            else:
                break

        sshCmdWithStderr('chmod 0755 %s' % dstScriptFile, host, sshKey=sshKey,
                         user=user, password=password)
    finally:
        try:
            os.unlink(scriptFile)
        except:
            pass

    return remoteRunCommand(user, host, dstScriptFile, sshKey, password, nohup)


def remoteRunScriptNohup(user, host, script, sshKey=None, password=''):
    return remoteRunScript(user, host, script, sshKey=sshKey, password=password, nohup=True)


def remoteRunCommand(user, host, command, sshKey=None, password='', nohup=False):
    if nohup:
        return remote_run_command_nohup(user, host, command, sshKey, password)
    else:
        return _remote_run_command(user, host, command, sshKey, password)

def _remote_run_command(user, host, command, sshKey=None, password=''):
    sudo = (user != 'root') and 'sudo' or ''
    cmd = ('%s %s' % (sudo, command)).strip()
    return sshCmdWithStderr(cmd, host, user, sshKey, password)


def remote_run_command_nohup(user, host, command, sshKey=None, password=''):
    sudo = (user != 'root') and 'sudo' or ''
    nohup_cmd = 'at now -f %s' % command
    cmd = ('%s %s' % (sudo, nohup_cmd)).strip()
    rc, stderr = sshCmdWithStderr(cmd, host, user, sshKey, password)
    if rc != 0:
        if re.search('.* (command )?not found.*', stderr, re.MULTILINE) or \
                not _remote_command_exists('at', host, user, sshKey, password):
            nohup_cmd = _remote_command_exists('nohup', host, user, sshKey, password) and 'nohup %s' or '%s'
            cmd = ('%s %s >/dev/null 2>&1 </dev/null &' % (sudo, nohup_cmd % command)).strip()
            rc, stderr = sshCmdWithStderr(cmd, host, user, sshKey, password)
            if rc != 0:
                raise Exceptions.ExecutionException("An error occurred while executing the command: %s\n%s." %
                                                    (command, stderr))
        else:
            raise Exceptions.ExecutionException("An error occurred while executing the command: %s\n%s." %
                                                (command, stderr))
    else:
        # Check stderr as atd may not be running, though return code was 0.
        # Starting atd service will start the command.
        if re.search('.*No atd running\?', stderr, re.MULTILINE):
            remote_start_service('atd', user, host, sshKey, password)

    return rc, stderr


def _remote_command_exists(command, user, host, sshKey=None, password=''):
    rc, stderr = sshCmdWithStderr('which %s' % command, host, user, sshKey, password)
    return rc == 0


def remote_start_service(service, user, host, sshKey=None, password=''):
    command = 'service %(s)s start || initctl start %(s)s || systemctl start %(s)s || /etc/init.d/%(s)s start' % \
              {'s': service}
    remoteRunCommand(user, host, command, sshKey, password)

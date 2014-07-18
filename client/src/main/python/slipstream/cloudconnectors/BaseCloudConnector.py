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

import re
import os
import time
import tempfile
import random
import string

from threading import local

import slipstream.exceptions.Exceptions as Exceptions

from slipstream import util, SlipStreamHttpClient
from slipstream.Client import Client
from slipstream.NodeDecorator import NodeDecorator, KEY_RUN_CATEGORY
from slipstream.listeners.SimplePrintListener import SimplePrintListener
from slipstream.listeners.SlipStreamClientListenerAdapter import SlipStreamClientListenerAdapter
from slipstream.utils.ssh import remoteRunScriptNohup, waitUntilSshCanConnectOrTimeout, remoteRunScript, \
                                 remoteInstallPackages, generate_keypair
from slipstream.utils.tasksrunner import TasksRunner
from slipstream.wrappers.BaseWrapper import NodeInfoPublisher
from winrm.winrm_service import WinRMWebService
from winrm.exceptions import WinRMTransportError


class BaseCloudConnector(object):

#   ----- METHODS THAT CAN/SHOULD BE IMPLEMENTED IN CONNECTORS -----

    def _initialization(self, user_info):
        """This method is called once before calling any others methods of the connector.
        This method can be used to some initialization tasks like configuring the Cloud driver."""
        pass

    def _finalization(self, user_info):
        """This method is called once when all instances have been started or if an exception has occurred."""
        pass

    def _start_image(self, user_info, node_instance, vm_name):
        """Cloud specific VM provisioning.
        Returns: node - cloud specific representation of a started VM."""
        raise NotImplementedError()

    def _build_image(self, user_info, node_instance):
        """This method is called during the Executing state of a build image. In most cases this method should call
        self._build_image_increment and then ask the Cloud to create an image from the instance.
        The return value should be the new Cloud image id."""
        raise NotImplementedError()

    def _wait_and_get_instance_ip_address(self, vm):
        """This method needs to be implemented by the connector if the latter not define the capability
        'direct_ip_assignment'."""
        return vm

    def _stop_deployment(self):
        """This method should terminate the full vapp if the connector has the vapp capability.
        This method should terminate all instances except the orchestrator if the connector don't has the vapp
        capability."""
        pass

    def _stop_vms_by_ids(self, ids):
        """This method should destroy all VMs corresponding to VMs IDs of the list."""
        raise NotImplementedError()

    def _stop_vapps_by_ids(self, ids):
        """This method is used to destroy a full vApp if the capability 'vapp' is set."""
        pass

    def _vm_get_id(self, vm_instance):
        """Retrieve the VM ID from the vm_instance object returned by _start_image().
        Returns: cloud ID of the instance."""
        raise NotImplementedError()

    def _vm_get_ip(self, vm_instance):
        """Retrieve an IP from the vm_instance object returned by _start_image().
        Returns: one IP - Public or Private."""
        raise NotImplementedError()

    def _vm_get_password(self, vm_instance):
        """Retrieve the password of the VM from the vm_instance object returned by _start_image().
        Returns: the password needed to connect to the VM"""
        pass

#   ----------------------------------------------------------------

    TIMEOUT_CONNECT = 10 * 60

    DISK_VOLATILE_PARAMETER_NAME = \
        (SlipStreamHttpClient.DomExtractor.EXTRADISK_PREFIX + '.volatile')
    DISK_PERSISTENT_PARAMETER_NAME = \
        (SlipStreamHttpClient.DomExtractor.EXTRADISK_PREFIX + '.persistent')

    RUN_BOOTSTRAP_SCRIPT = False
    WAIT_IP = False

    # CAPABILITIES
    CAPABILITY_VAPP = 'vapp'
    CAPABILITY_BUILD_IN_SINGLE_VAPP = 'buildInSingleVapp'
    CAPABILITY_CONTEXTUALIZATION = 'contextualization'
    CAPABILITY_WINDOWS_CONTEXTUALIZATION = 'windowsContextualization'
    CAPABILITY_GENERATE_PASSWORD = 'generatePassword'
    CAPABILITY_DIRECT_IP_ASSIGNMENT = 'directIpAssignment'
    CAPABILITY_NEED_TO_ADD_SHH_PUBLIC_KEY_ON_NODE = 'needToAddSshPublicKeyOnNode'
    CAPABILITY_ORCHESTRATOR_CAN_KILL_ITSELF_OR_ITS_VAPP = 'orchestratorCanKillItselfOrItsVapp'

    def __init__(self, configHolder):
        """Constructor.
        All connectors need to call this constructor from their own constructor.
        Moreover all connectors need to define their capabilities with the method _set_capabilities().
        """
        self.verboseLevel = 0
        configHolder.assign(self)
        self.configHolder = configHolder

        self.run_category = getattr(configHolder, KEY_RUN_CATEGORY, None)

        self.sshPrivKeyFile = '%s/.ssh/id_rsa' % os.path.expanduser("~")
        self.sshPubKeyFile = self.sshPrivKeyFile + '.pub'

        self.__listener = SimplePrintListener(verbose=(self.verboseLevel > 1))

        self.__vms = {}

        self.__cloud = os.environ['SLIPSTREAM_CONNECTOR_INSTANCE']

        self.__init_threading_related()

        self.tempPrivateKeyFileName = ''
        self.tempPublicKey = ''

        self.__capabilities = []

    def __init_threading_related(self):
        self.__tasks_runnner = None

        # This parameter is thread local
        self._thread_local = local()

    def _set_capabilities(self, vapp=False, build_in_single_vapp=False,
                          contextualization=False,
                          windows_contextualization=False,
                          generate_password=False,
                          direct_ip_assignment=False,
                          need_to_add_ssh_public_key_on_node=False,
                          orchestrator_can_kill_itself_or_its_vapp=False):
        if vapp:
            self.__capabilities.append(self.CAPABILITY_VAPP)
        if build_in_single_vapp:
            self.__capabilities.append(self.CAPABILITY_BUILD_IN_SINGLE_VAPP)
        if contextualization:
            self.__capabilities.append(self.CAPABILITY_CONTEXTUALIZATION)
        if windows_contextualization:
            self.__capabilities.append(self.CAPABILITY_WINDOWS_CONTEXTUALIZATION)
        if generate_password:
            self.__capabilities.append(self.CAPABILITY_GENERATE_PASSWORD)
        if direct_ip_assignment:
            self.__capabilities.append(self.CAPABILITY_DIRECT_IP_ASSIGNMENT)
        if need_to_add_ssh_public_key_on_node:
            self.__capabilities.append(
                self.CAPABILITY_NEED_TO_ADD_SHH_PUBLIC_KEY_ON_NODE)
        if orchestrator_can_kill_itself_or_its_vapp:
            self.__capabilities.append(
                self.CAPABILITY_ORCHESTRATOR_CAN_KILL_ITSELF_OR_ITS_VAPP)

    def _reset_capabilities(self):
        self.__capabilities = []

    def has_capability(self, capability):
        return capability in self.__capabilities

    def is_build_image(self):
        return self.run_category == NodeDecorator.IMAGE

    def is_deployment(self):
        return self.run_category == NodeDecorator.DEPLOYMENT

    @staticmethod
    def _get_max_workers(config_holder):
        try:
            ss = Client(config_holder)
            ss.ignoreAbort = True
            return ss.getRuntimeParameter('max.iaas.workers')
        except Exception as ex:  # pylint: disable=broad-except
            util.printDetail('Failed to get max.iaas.workers: %s' % str(ex),
                             verboseThreshold=0)
            return None

    def stop_deployment(self):
        self._stop_deployment()

    def stop_vms_by_ids(self, ids):
        self._stop_vms_by_ids(ids)

    def stop_vapps_by_ids(self, ids):
        self._stop_vapps_by_ids(ids)

    def start_nodes_and_clients(self, user_info, nodes_instances):

        self._initialization(user_info)
        try:
            self.__start_nodes_instantiation_tasks_wait_finished(user_info,
                                                                 nodes_instances)
        finally:
            self._finalization(user_info)

        return self.get_vms_details()

    def __start_nodes_instantiation_tasks_wait_finished(self, user_info,
                                                        nodes_instances):
        self.__start_nodes_instances_and_clients(user_info, nodes_instances)
        self.__wait_nodes_startup_tasks_finished()

    def __start_nodes_instances_and_clients(self, user_info, nodes_instances):
        max_workers = self._get_max_workers(self.configHolder)

        self.__tasks_runnner = TasksRunner(self.__start_node_instance_and_client,
                                           max_workers=max_workers,
                                           verbose=self.verboseLevel)

        for node_instance in nodes_instances.values():
            self.__tasks_runnner.put_task(user_info, node_instance)

        self.__tasks_runnner.run_tasks()

    def __wait_nodes_startup_tasks_finished(self):
        if self.__tasks_runnner != None:
            self.__tasks_runnner.wait_tasks_processed()

    def __start_node_instance_and_client(self, user_info, node_instance):
        node_instance_name = node_instance.get_name()

        self._print_detail("Starting instance: %s" % node_instance_name)

        vm = self._start_image(user_info,
                               node_instance,
                               self._generate_vm_name(node_instance_name))

        self.__add_vm(vm, node_instance)

        if not self.has_capability(self.CAPABILITY_DIRECT_IP_ASSIGNMENT):
            vm = self._wait_and_get_instance_ip_address(vm)
            self.__add_vm(vm, node_instance)

        if not self.has_capability(self.CAPABILITY_CONTEXTUALIZATION) and not self.is_build_image():
            if not node_instance.is_windows():
                self.__secure_ssh_access_and_run_bootstrap_script(
                    user_info, node_instance, self._vm_get_ip(vm))
            else:
                self.__launch_windows_bootstrap_script(node_instance,
                                                       self._vm_get_ip(vm))

    def __add_vm(self, vm, node_instance):
        name = node_instance.get_name()
        self.__vms[name] = vm
        self._publish_vm_info(vm, node_instance)

    def _publish_vm_info(self, vm, node_instance):
        instance_name = node_instance.get_name()
        self.__publish_vm_id(instance_name, self._vm_get_id(vm))
        self.__publish_vm_ip(instance_name, self._vm_get_ip(vm))
        if node_instance:
            self.__publish_url_ssh(vm, node_instance)

    def __publish_vm_id(self, instance_name, vm_id):
        # Needed for thread safety
        NodeInfoPublisher(self.configHolder).publish_instanceid(instance_name,
                                                                str(vm_id))

    def __publish_vm_ip(self, instance_name, vm_ip):
        # Needed for thread safety
        NodeInfoPublisher(self.configHolder).publish_hostname(instance_name,
                                                              vm_ip)

    def __publish_url_ssh(self, vm, node_instance):
        if not node_instance:
            return
        instance_name = node_instance.get_name()
        vm_ip = self._vm_get_ip(vm)
        ssh_username, _ = self.__get_vm_username_password(node_instance)

        # Needed for thread safety
        NodeInfoPublisher(self.configHolder).publish_url_ssh(instance_name,
                                                             vm_ip, ssh_username)

    def get_vms(self):
        return self.__vms

    def _get_vm(self, name):
        try:
            return self.__vms[name]
        except KeyError:
            raise Exceptions.NotFoundError("VM '%s' not found." % name)

    def _set_temp_private_key_and_public_key(self, privateKeyFileName, publicKey):
        self.tempPrivateKeyFileName = privateKeyFileName
        self.tempPublicKey = publicKey

    def _get_temp_private_key_file_name_and_public_key(self):
        return self.tempPrivateKeyFileName, self.tempPublicKey

    def build_image(self, user_info, node_instance):
        if not self.has_capability(self.CAPABILITY_CONTEXTUALIZATION):
            username, password = self.__get_vm_username_password(node_instance)
            privateKey, publicKey = generate_keypair()
            privateKey = util.file_put_content_in_temp_file(privateKey)
            self._set_temp_private_key_and_public_key(privateKey, publicKey)
            ip = self._vm_get_ip(self._get_vm(NodeDecorator.MACHINE_NAME))
            self._secure_ssh_access(ip, username, password, publicKey)

        new_id = self._build_image(user_info, node_instance)
        return new_id

    def get_creator_vm_id(self):
        vm = self._get_vm(NodeDecorator.MACHINE_NAME)
        return self._vm_get_id(vm)

    def _build_image_increment(self, user_info, node_instance, host):
        prerecipe = node_instance.get_prerecipe()
        recipe = node_instance.get_recipe()
        packages = ' '.join(node_instance.get_packages()).strip()
        try:
            machine_name = node_instance.get_name()

            username, password, ssh_private_key_file = self._get_ssh_credentials(node_instance, user_info)

            if not self.has_capability(self.CAPABILITY_CONTEXTUALIZATION) and not ssh_private_key_file:
                password = ''
                ssh_private_key_file, publicKey = self._get_temp_private_key_file_name_and_public_key()

            self._wait_can_connect_with_ssh_or_abort(host, username=username,
                                               password=password,
                                               sshKey=ssh_private_key_file)

            if prerecipe:
                util.printStep('Running Pre-recipe')
                self.__listener.write_for(machine_name, 'Running Pre-recipe')
                remoteRunScript(username, host, prerecipe, sshKey=ssh_private_key_file, password=password)
            if packages:
                util.printStep('Installing Packages')
                self.__listener.write_for(machine_name, 'Installing Packages')
                remoteInstallPackages(username, host, packages,
                                      node_instance.get_platform(),
                                      sshKey=ssh_private_key_file,
                                      password=password)
            if recipe:
                util.printStep('Running Recipe')
                self.__listener.write_for(machine_name, 'Running Recipe')
                remoteRunScript(username, host, recipe, sshKey=ssh_private_key_file, password=password)

            if not self.has_capability(self.CAPABILITY_CONTEXTUALIZATION):
                self._revert_ssh_security(host, username, ssh_private_key_file, publicKey)
        finally:
            try:
                os.unlink(ssh_private_key_file)
            except:  # pylint: disable=bare-except
                pass

    def get_cloud_service_name(self):
        return self.__cloud

    def _get_ssh_credentials(self, node_instance, user_info):
        username, password = self.__get_vm_username_password(node_instance)
        if password:
            ssh_private_key_file = None
        else:
            ssh_private_key_file = self.__get_ssh_private_key_file(user_info)
        return username, password, ssh_private_key_file

    def __get_ssh_private_key_file(self, user_info):
        fd, ssh_private_key_file = tempfile.mkstemp()
        os.write(fd, user_info.get_private_key())
        os.close(fd)
        os.chmod(ssh_private_key_file, 0400)
        return ssh_private_key_file

    def __get_vm_username_password(self, node_instance):
        user = node_instance.get_username('root')
        password = self.__get_vm_password(node_instance)
        return user, password

    def __get_vm_password(self, node_instance):
        password = node_instance.get_password()
        if not password:
            instance_name = node_instance.get_name()
            try:
                vm = self._get_vm(instance_name)
                password = self._vm_get_password(vm)
            except:  # pylint: disable=bare-except
                pass
        return password

    @staticmethod
    def _generate_vm_name(instance_name):
        vm_name = instance_name
        run_id = os.environ.get('SLIPSTREAM_DIID', None)
        if run_id:
            vm_name = vm_name + NodeDecorator.NODE_PROPERTY_SEPARATOR + run_id
        return vm_name

    @staticmethod
    def isStartOrchestrator():
        return os.environ.get('CLI_ORCHESTRATOR', 'False') == 'True'

    def __secure_ssh_access_and_run_bootstrap_script(self, user_info, node_instance, ip):
        username, password = self.__get_vm_username_password(node_instance)

        privateKey, publicKey = generate_keypair()
        privateKey = util.file_put_content_in_temp_file(privateKey)

        self._secure_ssh_access(ip, username, password, publicKey, user_info)
        self.__launch_bootstrap_script(node_instance, ip, username, privateKey)

    def _secure_ssh_access(self, ip, username, password, publicKey, user_info=None):
        self._wait_can_connect_with_ssh_or_abort(ip, username, password)
        script = self.__get_obfuscation_script(publicKey, username, user_info)
        self._print_detail("Securing SSH access to %s with:\n%s\n" % (ip,
                                                                     script))
        _, output = self._run_script(ip, username, script, password=password)
        self._print_detail("Secured SSH access to %s. Output:\n%s\n" % (ip,
                                                                       output))

    def _revert_ssh_security(self, ip, username, privateKey, orchestratorPublicKey):
        self._wait_can_connect_with_ssh_or_abort(ip, username, sshKey=privateKey)
        script = "#!/bin/bash -xe\n"
        script += "set +e\n"
        script += "grep -vF '" + orchestratorPublicKey + "' ~/.ssh/authorized_keys > ~/.ssh/authorized_keys.tmp\n"
        script += "set -e\n"
        script += "sleep 2\nmv ~/.ssh/authorized_keys.tmp ~/.ssh/authorized_keys\n"
        script += "chown -R " + username + ":$(id -g " + username + ")" + " ~/.ssh\n"
        script += "restorecon -Rv ~/.ssh || true\n"
        script += "sed -i -r 's/^#?[\\t ]*(PasswordAuthentication[\\t ]+)((yes)|(no))/\\1yes/' /etc/ssh/sshd_config\n"
        script += "sync\nsleep 2\n"
        script += "[ -x /etc/init.d/sshd ] && { service sshd reload; } || { service ssh reload || /etc/init.d/ssh reload; }\n"
        self._print_detail("Reverting security of SSH access to %s with:\n%s\n" % (ip, script))
        _, output = self._run_script(ip, username, script, sshKey=privateKey)
        self._print_detail("Reverted security of SSH access to %s. Output:\n%s\n" % (ip, output))

    def __launch_bootstrap_script(self, node_instance, ip, username, privateKey):
        self._wait_can_connect_with_ssh_or_abort(ip, username, sshKey=privateKey)
        script = self._get_bootstrap_script(node_instance)
        self._print_detail("Launching bootstrap script on %s:\n%s\n" % (ip,
                                                                       script))
        _, output = self._run_script_on_backgroud(ip, username, script,
                                               sshKey=privateKey)
        self._print_detail("Launched bootstrap script on %s:\n%s\n" % (ip,
                                                                      output))

    def __launch_windows_bootstrap_script(self, node_instance, ip):
        username, password = self.__get_vm_username_password(node_instance)
        script = self._get_bootstrap_script(node_instance, username=username)
        winrm = self._getWinrm(ip, username, password)
        self._waitCanConnectWithWinrmOrAbort(winrm)
        self._print_detail("Launching bootstrap script on %s:\n%s\n" % (ip,
                                                                       script))
        util.printAndFlush(script)
        winrm.timeout = winrm.set_timeout(600)
        output = self._runScriptWithWinrm(winrm, script)
        self._print_detail("Launched bootstrap script on %s:\n%s\n" % (ip,
                                                                      output))

    def _getWinrm(self, ip, username, password):
        return WinRMWebService(endpoint='http://%s:5985/wsman' % ip,
                               transport='plaintext', username=username,
                               password=password)

    def _runScriptWithWinrm(self, winrm, script):
        shellId = winrm.open_shell()
        commands = ''
        for command in script.splitlines():
            if command:
                commands += command + '& '
        commands += 'echo "Bootstrap Finished"'
        stdout, stderr, returnCode = self._runCommandWithWinrm(winrm, commands,
                                                               shellId,
                                                               runAndContinue=True)
        # winrm.close_shell(shellId)
        return stdout, stderr, returnCode

    def _waitCanConnectWithWinrmOrAbort(self, winrm):
        try:
            self._waitCanConnectWithWinrmOrTimeout(winrm, self.TIMEOUT_CONNECT)
        except Exception as ex:
            raise Exceptions.ExecutionException("Failed to connect to "
                                                "%s: %s" % (winrm.endpoint,
                                                            str(ex)))

    def _waitCanConnectWithWinrmOrTimeout(self, winrm, timeout):
        time_stop = time.time() + timeout
        while (time_stop - time.time()) >= 0:
            try:
                _, _, returnCode = self._runCommandWithWinrm(winrm, 'exit 0')
                if returnCode == 0:
                    return
            except WinRMTransportError as ex:
                util.printDetail(str(ex))
                time.sleep(5)

    def _runCommandWithWinrm(self, winrm, command, shellId=None,
                             runAndContinue=False):
        if shellId:
            _shellId = shellId
        else:
            _shellId = winrm.open_shell()
        util.printAndFlush('\nwinrm.run_command\n')
        commandId = winrm.run_command(_shellId, command, [])
        stdout, stderr, returnCode = ('N/A', 'N/A', 0)
        util.printAndFlush('\nwinrm.get_command_output\n')
        if not runAndContinue:
            try:
                stdout, stderr, returnCode = winrm.get_command_output(_shellId, commandId)
            except Exception as e:  # pylint: disable=broad-except
                print 'WINRM Exception: %s' % str(e)
        util.printAndFlush('\nwinrm.cleanup_command\n')
        if not runAndContinue:
            winrm.cleanup_command(_shellId, commandId)
            if not shellId:
                winrm.close_shell(_shellId)
        return stdout, stderr, returnCode

    def __get_obfuscation_script(self, orchestrator_public_key, username, user_info=None):
        command = "#!/bin/bash -xe\n"
        # command += "sed -r -i 's/# *(account +required +pam_access\\.so).*/\\1/' /etc/pam.d/login\n"
        # command += "echo '-:ALL:LOCAL' >> /etc/security/access.conf\n"
        command += "sed -i -r '/^[\\t ]*RSAAuthentication/d;/^[\\t ]*PubkeyAuthentication/d;/^[\\t ]*PasswordAuthentication/d' /etc/ssh/sshd_config\n"
        command += "echo 'RSAAuthentication yes\nPubkeyAuthentication yes\nPasswordAuthentication no\n' >> /etc/ssh/sshd_config\n"
        # command += "sed -i -r 's/^#?[\\t ]*(RSAAuthentication[\\t ]+)((yes)|(no))/\\1yes/' /etc/ssh/sshd_config\n"
        # command += "sed -i -r 's/^#?[\\t ]*(PubkeyAuthentication[\\t ]+)((yes)|(no))/\\1yes/' /etc/ssh/sshd_config\n"
        # command += "sed -i -r 's/^#?[\t ]*(PasswordAuthentication[\\t ]+)((yes)|(no))/\\1no/' /etc/ssh/sshd_config\n"
        command += "umask 077\n"
        command += "mkdir -p ~/.ssh\n"
        if user_info:
            command += "echo '" + user_info.get_public_keys() + "' >> ~/.ssh/authorized_keys\n"
        command += "echo '" + orchestrator_public_key + "' >> ~/.ssh/authorized_keys\n"
        command += "chown -R " + username + ":$(id -g " + username + ")" + " ~/.ssh\n"
        command += "restorecon -Rv ~/.ssh || true\n"
        command += "[ -x /etc/init.d/sshd ] && { service sshd reload; } || { service ssh reload; }\n"
        return command

    def _get_bootstrap_script(self, node_instance, pre_export=None,
                              pre_bootstrap=None, post_bootstrap=None,
                              username=None):
        """This method can be redefined by connectors if they need a specific bootstrap script
        with the SSH contextualization."""
        script = ''
        addEnvironmentVariableCommand = ''
        node_instance_name = node_instance.get_name()

        if node_instance.is_windows():
            addEnvironmentVariableCommand = 'set'
        else:
            addEnvironmentVariableCommand = 'export'
            script += '#!/bin/sh -ex\n'

        if pre_export:
            script += '%s\n' % pre_export
        util.printAndFlush(str(os.environ))

        for var, val in os.environ.items():
            if var.startswith('SLIPSTREAM_') and var != 'SLIPSTREAM_NODENAME':
                if var == 'SLIPSTREAM_REPORT_DIR' and node_instance.is_windows():
                    val = Client.WINDOWS_REPORTSDIR
                if re.search(' ', val):
                    val = '"%s"' % val
                script += '%s %s=%s\n' % (addEnvironmentVariableCommand, var,
                                          val)

        script += '%s SLIPSTREAM_NODENAME=%s\n' % (addEnvironmentVariableCommand,
                                                   node_instance_name)

        script += '%s %s=%s\n' % (addEnvironmentVariableCommand,
                                  util.ENV_NEED_TO_ADD_SSHPUBKEY,
                                  self.has_capability(self.CAPABILITY_NEED_TO_ADD_SHH_PUBLIC_KEY_ON_NODE))

        if pre_bootstrap:
            script += '%s\n' % pre_bootstrap

        script += '%s\n' % self._build_slipstream_bootstrap_command(node_instance,
                                                                    username)

        if post_bootstrap:
            script += '%s\n' % post_bootstrap

        return script

    def _build_slipstream_bootstrap_command(self, node_instance, username=None):
        instance_name = node_instance.get_name()

        if node_instance.is_windows():
            return self.__build_slipstream_bootstrap_command_for_windows(instance_name, username)
        else:
            return self.__build_slipstream_bootstrap_command_for_linux(instance_name)

    def __build_slipstream_bootstrap_command_for_windows(self, instance_name,
                                                   username):
        if not username:
            username = 'administrator'
        bootstrap = 'slipstream.bootstrap'
        reportdir = Client.WINDOWS_REPORTSDIR

        targetScript = ''
        if self.isStartOrchestrator():
            targetScript = 'slipstream-orchestrator'

        command = 'mkdir %(reports)s\n'
        command += 'powershell -Command "$wc = New-Object System.Net.WebClient; $wc.DownloadFile(\'http://www.python.org/ftp/python/2.7.4/python-2.7.4.msi\', $env:temp+\'\\python.msi\')"\n'
        command += 'start /wait msiexec /i %%TMP%%\\python.msi /qn /quiet /norestart /log log.txt TARGETDIR=C:\\Python27\\ ALLUSERS=1\n'
        command += 'setx path "%%path%%;C:\\Python27" /M\n'
        command += 'powershell -Command "[System.Net.ServicePointManager]::ServerCertificateValidationCallback = {$true}; $wc = New-Object System.Net.WebClient; $wc.Headers.Add(\'User-Agent\',\'PowerShell\'); $wc.DownloadFile(\'%(bootstrapUrl)s\', $env:temp+\'\\%(bootstrap)s\')" > %(reports)s\\%(nodename)s.slipstream.log 2>&1\n'
        command += 'set PATH=%%PATH%%;C:\\Python27;C:\\opt\\slipstream\\client\\bin\n'
        command += 'set PYTHONPATH=C:\\opt\\slipstream\\client\\lib\n'

        password = ''
        if not self.has_capability(self.CAPABILITY_GENERATE_PASSWORD):
            password = ''.join(random.choice(string.ascii_letters + string.digits)
                               for _ in range(10))
            command += 'set pass=%(password)s\n'
            command += 'net user %(username)s %%pass%%\n'
            command += 'ss-get nodename > tmp.txt\n'
            command += 'set /p nodename= < tmp.txt\n'
            command += 'ss-get index > tmp.txt\n'
            command += 'set /p index= < tmp.txt\n'
            command += 'ss-get cloudservice > tmp.txt\n'
            command += 'set /p cloudservice= < tmp.txt\n'
            command += 'del tmp.txt\n'
            command += 'ss-set %%nodename%%.%%index%%:%%cloudservice%%.login.password %%pass%%\n'

        # command += 'C:\\Python27\\python %%TMP%%\\%(bootstrap)s >> %(reports)s\%(nodename)s.slipstream.log 2>&1\n'
        command += 'start "test" "%%SystemRoot%%\System32\cmd.exe" /C "C:\\Python27\\python %%TMP%%\\%(bootstrap)s %(targetScript)s >> %(reports)s\\%(nodename)s.slipstream.log 2>&1"\n'

        return command % {
            'bootstrap': bootstrap,
            'bootstrapUrl': os.environ['SLIPSTREAM_BOOTSTRAP_BIN'],
            'reports': reportdir,
            'nodename': instance_name,
            'username': username,
            'password': password,
            'targetScript': targetScript
        }

    def __build_slipstream_bootstrap_command_for_linux(self, instance_name):
        bootstrap = os.path.join(tempfile.gettempdir(), 'slipstream.bootstrap')
        reportdir = Client.REPORTSDIR

        targetScript = ''
        if self.isStartOrchestrator():
            targetScript = 'slipstream-orchestrator'

        command = 'mkdir -p %(reports)s; wget --no-check-certificate --secure-protocol=SSLv3 -O %(bootstrap)s %(bootstrapUrl)s >%(reports)s/%(nodename)s.slipstream.log 2>&1 && chmod 0755 %(bootstrap)s; %(bootstrap)s %(targetScript)s >>%(reports)s/%(nodename)s.slipstream.log 2>&1'
        return command % {
            'bootstrap': bootstrap,
            'bootstrapUrl': os.environ['SLIPSTREAM_BOOTSTRAP_BIN'],
            'reports': reportdir,
            'nodename': instance_name,
            'targetScript': targetScript
        }

    def _wait_can_connect_with_ssh_or_abort(self, host, username='', password='', sshKey=None):
        self._print_detail('Check if we can connect to %s' % host)
        try:
            waitUntilSshCanConnectOrTimeout(host,
                                            self.TIMEOUT_CONNECT,
                                            sshKey=sshKey,
                                            user=username, password=password)
        except Exception as ex:
            raise Exceptions.ExecutionException("Failed to connect to "
                                                "%s: %s, %s" % (host, type(ex),
                                                                str(ex)))

    def _run_script(self, ip, username, script, password='', sshKey=None):
        return remoteRunScript(username, ip, script, sshKey=sshKey, password=password)

    def _run_script_on_backgroud(self, ip, username, script, password='', sshKey=None):
        return remoteRunScriptNohup(username, ip, script, sshKey=sshKey, password=password)

    def set_slipstream_client_as_listener(self, client):
        self._set_listener(SlipStreamClientListenerAdapter(client))

    def _set_listener(self, listener):
        self.__listener = listener

    def _get_listener(self):
        return self.__listener

    def _print_detail(self, message):
        util.printDetail(message, self.verboseLevel)

    def get_vms_details(self):
        vms_details = []
        for name, vm in self.get_vms().items():
            vms_details.append({name: {'id': self._vm_get_id(vm),
                                       'ip': self._vm_get_ip(vm)}})
        return vms_details

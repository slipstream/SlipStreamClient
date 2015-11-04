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
import sys

from threading import local
from threading import Lock

import slipstream.exceptions.Exceptions as Exceptions

from slipstream import util, SlipStreamHttpClient
from slipstream.Client import Client
from slipstream.NodeDecorator import NodeDecorator, KEY_RUN_CATEGORY
from slipstream.listeners.SimplePrintListener import SimplePrintListener
from slipstream.listeners.SlipStreamClientListenerAdapter import SlipStreamClientListenerAdapter
from slipstream.utils.ssh import remoteRunScriptNohup, waitUntilSshCanConnectOrTimeout, remoteRunScript, \
                                 generate_keypair, remoteRunCommand
from slipstream.utils.tasksrunner import TasksRunner
from slipstream.cloudconnectors.VmScaler import VmScaler
from slipstream.wrappers.BaseWrapper import NodeInfoPublisher
from winrm.winrm_service import WinRMWebService
from winrm.exceptions import WinRMTransportError

lock = Lock()


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
        self._build_image_increment() and then ask the Cloud to create an image from the instance.
        The return value should be the new Cloud image id as a string."""
        raise NotImplementedError()

    def _wait_and_get_instance_ip_address(self, vm):
        """This method needs to be implemented by the connector if the latter not define the capability
        'direct_ip_assignment'."""
        return vm

    def _stop_deployment(self):
        """This method should terminate the full vapp if the connector has the vapp capability.
        This method should terminate all instances except the orchestrator if the connector doesn't have the vapp
        capability."""
        pass

    def _stop_vms_by_ids(self, ids):
        """This method should destroy all VMs corresponding to VMs IDs of the list."""
        raise NotImplementedError()

    def _stop_vapps_by_ids(self, ids):
        """This method is used to destroy a full vApp if the capability 'vapp' is set."""
        pass

    def list_instances(self):
        """Returns list of VMs consumable by the connector's _vm_get_id(vm) and _vm_get_ip(vm).
        """
        raise NotImplementedError()

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

    def _vm_get_state(self, vm_instance):
        """Retrieve VM state from the vm_instance object returned by list_instances().
        Returns: VM cloud state."""
        return ""

    def _create_allow_all_security_group(self):
        """If the conncector support security groups, this method should create a security group named
        NodeDecorator.SECURITY_GROUP_ALLOW_ALL_NAME with everything allowed if it doesn't exist yet."""
        pass

    ''' The methods below are used to generate the reply of *-describe-instances
    '''

    def _vm_get_ip_from_list_instances(self, vm_instance):
        """Retrieve an IP from the vm_instance object returned by list_instances().
        Returns: one IP - Public or Private."""
        pass

    def _vm_get_cpu(self, vm_instance):
        """Retrieve the number of CPU of the VM from the vm_instance object returned by list_instances().
        Returns: the number of CPU of VM"""
        pass

    def _vm_get_ram(self, vm_instance):
        """Retrieve the amount of RAM memory of the VM from the vm_instance object returned by list_instances().
        Returns: the amount of RAM memory of the VM in MB"""
        pass

    def _vm_get_root_disk(self, vm_instance):
        """Retrieve the size of the root disk of the VM from the vm_instance object returned by list_instances().
        Returns: the size of the root disk of the VM in GB"""
        pass

    def _vm_get_instance_type(self, vm_instance):
        """Retrieve the instance type of the VM from the vm_instance object returned by list_instances().
        Returns: the name of the instance type of the VM"""
        pass

    def _get_vm_failed_states(self):
        """Override the method or provide cloud specific list of VM_FAILED_STATES.
        """
        return self.VM_FAILED_STATES


    """IaaS actions for VM vertical scalability.

    If the VM needs to be restarted, the implementation should
    * wait until VM enters Running state, and
    * assert that the action was correctly fulfilled by IaaS.
    If the action on the VM can be applied w/o restart, the implementation should
    * wait until action is applied by IaaS, and
    * assert that the action was correctly fulfilled by IaaS.
    Raise `slipstream.exceptions.Exceptions.ExecutionException`
    on any handled error.
    """

    def _resize(self, node_instance):
        """
        :param node_instance: node instance object
        :type node_instance: <NodeInstance>
        """

        # Example code

        # Cloud VM id.
        #vm_id = node_instance.get_instance_id()

        # RAM in GB.
        #ram = node_instance.get_ram()
        # Number of CPUs.
        #cpu = node_instance.get_cpu()

        # In case cloud uses T-short sizes.
        #instance_type = node_instance.get_instance_type()

        # IaaS calls go here.

        raise NotImplementedError()

    def _attach_disk(self, node_instance):
        """Attach extra disk to the VM.
        :param node_instance: node instance object
        :type node_instance: <NodeInstance>
        :return: name of the device that was attached
        :rtype: string
        """

        # Example code

        #device_name = ''

        # Cloud VM id.
        #vm_id = node_instance.get_instance_id()

        # Size of the disk to attach (in GB).
        #disk_size_GB = node_instance.get_disk_attach_size()

        # IaaS calls go here.

        #return device_name

        raise NotImplementedError()

    def _detach_disk(self, node_instance):
        """Detach disk from the VM.
        :param node_instance: node instance object
        :type node_instance: <NodeInstance>
        """

        # Example code

        # Cloud VM id.
        #vm_id = node_instance.get_instance_id()

        # Name of the block device to detach (/dev/XYZ).
        #device = node_instance.get_disk_detach_device()

        # IaaS calls go here.

        raise NotImplementedError()

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
    CAPABILITY_ORCHESTRATOR_CAN_KILL_ITSELF_OR_ITS_VAPP = 'orchestratorCanKillItselfOrItsVapp'

    VM_FAILED_STATES = ['failed', 'error']

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

        self.__cloud = os.environ[util.ENV_CONNECTOR_INSTANCE]

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
        if orchestrator_can_kill_itself_or_its_vapp:
            self.__capabilities.append(
                self.CAPABILITY_ORCHESTRATOR_CAN_KILL_ITSELF_OR_ITS_VAPP)

    def _reset_capabilities(self):
        self.__capabilities = []

    def has_capability(self, capability):
        return capability in self.__capabilities

    def __set_contextualization_capabilities(self, user_info):
        native_contextualization = user_info.get_cloud(NodeDecorator.NATIVE_CONTEXTUALIZATION_KEY, None)
        if native_contextualization:
            try:
                self.__capabilities.remove(self.CAPABILITY_CONTEXTUALIZATION)
                self.__capabilities.remove(self.CAPABILITY_WINDOWS_CONTEXTUALIZATION)
            except ValueError:
                pass

            if native_contextualization == 'always':
                self.__capabilities.append(self.CAPABILITY_CONTEXTUALIZATION)
                self.__capabilities.append(self.CAPABILITY_WINDOWS_CONTEXTUALIZATION)
            elif native_contextualization == 'linux-only':
                self.__capabilities.append(self.CAPABILITY_CONTEXTUALIZATION)
            elif native_contextualization == 'windows-only':
                self.__capabilities.append(self.CAPABILITY_WINDOWS_CONTEXTUALIZATION)

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
            util.printDetail('Failed to get max.iaas.workers: %s %s' %
                             (ex.__class__, str(ex)), verboseThreshold=0)
            return None

    def stop_deployment(self):
        self._stop_deployment()

    def stop_vms_by_ids(self, ids):
        self._stop_vms_by_ids(ids)

    def stop_vapps_by_ids(self, ids):
        self._stop_vapps_by_ids(ids)

    def stop_node_instances(self, node_instances):
        ids = []

        for node_instance in node_instances:
            ids.append(node_instance.get_instance_id())
            self.__del_vm(node_instance.get_name())

        if len(ids) > 0:
            self.stop_vms_by_ids(ids)

    def __create_allow_all_security_group_if_needed(self, nodes_instances):
        sg_key = NodeDecorator.SECURITY_GROUPS_KEY
        sg_name = NodeDecorator.SECURITY_GROUP_ALLOW_ALL_NAME

        for ni in nodes_instances.itervalues():
            if ni.get_cloud_parameter(sg_key, '').strip() == sg_name:
                self._create_allow_all_security_group()
                break

    def start_nodes_and_clients(self, user_info, nodes_instances, init_extra_kwargs={}):
        self._initialization(user_info, **init_extra_kwargs)
        self.__set_contextualization_capabilities(user_info)
        self.__create_allow_all_security_group_if_needed(nodes_instances)
        try:
            self.__start_nodes_instantiation_tasks_wait_finished(user_info,
                                                                 nodes_instances)
        finally:
            self._finalization(user_info)

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

        if not self.is_build_image():
            if not node_instance.is_windows() and not self.has_capability(self.CAPABILITY_CONTEXTUALIZATION):
                self.__secure_ssh_access_and_run_bootstrap_script(user_info, node_instance, self._vm_get_ip(vm))

            elif node_instance.is_windows() and not self.has_capability(self.CAPABILITY_WINDOWS_CONTEXTUALIZATION):
                self.__launch_windows_bootstrap_script(node_instance, self._vm_get_ip(vm))

    def get_vms(self):
        return self.__vms

    def _get_vm(self, name):
        try:
            return self.__vms[name]
        except KeyError:
            raise Exceptions.NotFoundError("VM '%s' not found." % name)

    def __add_vm(self, vm, node_instance):
        name = node_instance.get_name()
        with lock:
            self.__vms[name] = vm
        self._publish_vm_info(vm, node_instance)

    def __del_vm(self, name):
        try:
            del self.__vms[name]
        except KeyError:
            util.printDetail("Failed locally removing VM '%s'. Not found." % name)

    def _publish_vm_info(self, vm, node_instance):
        instance_name = node_instance.get_name()
        vm_id = self._vm_get_id(vm)
        vm_ip = self._vm_get_ip(vm)
        if vm_id:
            self._publish_vm_id(instance_name, vm_id)
        if vm_ip:
            self._publish_vm_ip(instance_name, vm_ip)
        if node_instance and vm_ip:
            self._publish_url_ssh(vm, node_instance)

    def _publish_vm_id(self, instance_name, vm_id):
        # Needed for thread safety
        NodeInfoPublisher(self.configHolder).publish_instanceid(instance_name,
                                                                str(vm_id))

    def _publish_vm_ip(self, instance_name, vm_ip):
        # Needed for thread safety
        NodeInfoPublisher(self.configHolder).publish_hostname(instance_name,
                                                              vm_ip)

    def _publish_url_ssh(self, vm, node_instance):
        if not node_instance:
            return
        instance_name = node_instance.get_name()
        vm_ip = self._vm_get_ip(vm) or ''
        ssh_username, _ = self.__get_vm_username_password(node_instance)

        # Needed for thread safety
        NodeInfoPublisher(self.configHolder).publish_url_ssh(instance_name,
                                                             vm_ip, ssh_username)

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
        packages = node_instance.get_packages()
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
                self._print_step('Running Pre-recipe', machine_name)
                remoteRunScript(username, host, prerecipe, sshKey=ssh_private_key_file, password=password)

            if packages:
                self._print_step('Installing Packages', machine_name)
                platform = node_instance.get_platform()
                remoteRunCommand(command=util.get_packages_install_command(platform, packages),
                                 host=host, user=username, sshKey=ssh_private_key_file, password=password)

            if recipe:
                self._print_step('Running Recipe', machine_name)
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

    def __get_vm_username_password(self, node_instance, default_user='root'):
        user = node_instance.get_username(default_user)
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
    def is_start_orchestrator():
        return os.environ.get('IS_ORCHESTRATOR', 'False') == 'True'

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
        username, password = self.__get_vm_username_password(node_instance, 'administrator')

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
            if command and not command.startswith('rem '):
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

        if not runAndContinue:
            util.printAndFlush('\nwinrm.get_command_output\n')
            try:
                stdout, stderr, returnCode = winrm.get_command_output(_shellId, commandId)
            except Exception as e:  # pylint: disable=broad-except
                print 'WINRM Exception: %s' % str(e)

            util.printAndFlush('\nwinrm.cleanup_command\n')
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
            script += 'rem cmd\n'
        else:
            addEnvironmentVariableCommand = 'export'
            script += '#!/bin/sh -ex\n'

        regex = 'SLIPSTREAM_'
        if self.is_start_orchestrator():
            regex += '|CLOUDCONNECTOR_'
        env_matcher = re.compile(regex)

        if pre_export:
            script += '%s\n' % pre_export

        for var, val in os.environ.items():
            if env_matcher.match(var) and var != util.ENV_NODE_INSTANCE_NAME:
                if re.search(' ', val):
                    val = '"%s"' % val
                script += '%s %s=%s\n' % (addEnvironmentVariableCommand, var,
                                          val)

        script += '%s %s=%s\n' % (addEnvironmentVariableCommand,
                                  util.ENV_NODE_INSTANCE_NAME,
                                  node_instance_name)

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
            return self.__build_slipstream_bootstrap_command_for_windows(instance_name)
        else:
            return self.__build_slipstream_bootstrap_command_for_linux(instance_name)

    def __build_slipstream_bootstrap_command_for_windows(self, instance_name):

        command = 'If Not Exist %(reports)s mkdir %(reports)s\n'
        command += 'If Not Exist %(ss_home)s mkdir %(ss_home)s\n'
        command += 'If Not Exist "C:\\Python27\\python.exe" ( '
        command += '  powershell -Command "$wc = New-Object System.Net.WebClient; $wc.DownloadFile(\'https://www.python.org/ftp/python/2.7.10/python-2.7.10.amd64.msi\', $env:temp+\'\\python.msi\')"\n'
        command += '  start /wait msiexec /i %%TMP%%\\python.msi /qn /quiet /norestart /log log.txt TARGETDIR=C:\\Python27\\ ALLUSERS=1 '
        command += ')\n'
        command += 'setx path "%%path%%;C:\\Python27;C:\\opt\\slipstream\\client\\bin;C:\\opt\\slipstream\\client\\sbin" /M\n'
        command += 'setx PYTHONPATH "%%PYTHONPATH%%;C:\\opt\\slipstream\\client\\lib" /M\n'
        command += 'powershell -Command "[System.Net.ServicePointManager]::ServerCertificateValidationCallback = {$true}; $wc = New-Object System.Net.WebClient; $wc.Headers.Add(\'User-Agent\',\'PowerShell\'); $wc.DownloadFile(\'%(bootstrapUrl)s\', $env:temp+\'\\%(bootstrap)s\')" > %(reports)s\\%(nodename)s.slipstream.log 2>&1\n'
        command += 'set PATH=%%PATH%%;C:\\Python27;C:\\opt\\slipstream\\client\\bin;C:\\opt\\slipstream\\client\\sbin\n'
        command += 'set PYTHONPATH=C:\\opt\\slipstream\\client\\lib\n'

        command += 'start "test" "%%SystemRoot%%\System32\cmd.exe" /C "C:\\Python27\\python C:\\%(bootstrap)s %(machine_executor)s >> %(reports)s\\%(nodename)s.slipstream.log 2>&1"\n'

        return command % self._get_bootstrap_command_replacements(instance_name, Client.WINDOWS_REPORTSDIR)

    def __build_slipstream_bootstrap_command_for_linux(self, instance_name):

        command = 'mkdir -p %(reports)s %(ss_home)s; '
        command += '(wget --no-check-certificate -O %(bootstrap)s %(bootstrapUrl)s >> %(reports)s/%(nodename)s.slipstream.log 2>&1 '
        command += '|| curl -k -f -o %(bootstrap)s %(bootstrapUrl)s >> %(reports)s/%(nodename)s.slipstream.log 2>&1) '
        command += '&& chmod 0755 %(bootstrap)s; %(bootstrap)s %(machine_executor)s >> %(reports)s/%(nodename)s.slipstream.log 2>&1'

        return command % self._get_bootstrap_command_replacements(instance_name, Client.REPORTSDIR)

    def _get_bootstrap_command_replacements(self, instance_name, reports_dir):
        return {
            'reports': reports_dir,
            'bootstrap': os.path.join(util.SLIPSTREAM_HOME, 'slipstream.bootstrap'),
            'bootstrapUrl': util.get_required_envvar('SLIPSTREAM_BOOTSTRAP_BIN'),
            'ss_home': util.SLIPSTREAM_HOME,
            'nodename': instance_name,
            'machine_executor': self._get_machine_executor_type()
        }

    def _get_machine_executor_type(self):
        return self.is_start_orchestrator() and 'orchestrator' or 'node'

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

    def _print_step(self, message, write_for=None):
        util.printStep(message)
        if write_for:
            self._get_listener().write_for(write_for, message)

    def get_vms_details(self):
        vms_details = []
        for name, vm in self.get_vms().items():
            vms_details.append({name: {'id': self._vm_get_id(vm),
                                       'ip': self._vm_get_ip(vm)}})
        return vms_details

    def _has_vm_failed(self, vm_instance):
        """Check if VM failed on the cloud level. vm_instance as returned by _start_image().
        Returns: True or False."""
        vm_state = self._vm_get_state(vm_instance).lower()
        return vm_state in [fstate.lower() for fstate in self._get_vm_failed_states()]

    def resize(self, node_instances, done_reporter=None):
        self._scale_action_runner(self._resize_and_report, node_instances, done_reporter)

    # TODO: use decorator for reporter.
    def _resize_and_report(self, node_instance, reporter):
        self._resize(node_instance)
        if hasattr(reporter, '__call__'):
            reporter(node_instance)

    def attach_disk(self, node_instances, done_reporter=None):
        self._scale_action_runner(self._attach_disk_and_report, node_instances, done_reporter)

    def _attach_disk_and_report(self, node_instance, reporter):
        attached_disk = self._attach_disk(node_instance)
        if not attached_disk:
            raise Exceptions.ExecutionException('Attached disk name not provided by connector after disk attach operation.')
        if hasattr(reporter, '__call__'):
            reporter(node_instance, attached_disk)

    def detach_disk(self, node_instances, done_reporter=None):
        self._scale_action_runner(self._detach_disk_and_report, node_instances, done_reporter)

    def _detach_disk_and_report(self, node_instance, reporter):
        self._detach_disk(node_instance)
        if hasattr(reporter, '__call__'):
            reporter(node_instance)

    def _scale_action_runner(self, scale_action, node_instances, done_reporter):
        """
        :param scale_action: task executor
        :type scale_action: callable
        :param node_instances: list of node instances
        :type node_instances: list [NodeInstance, ]
        :param done_reporter: function that reports back to SlipStream
        :type done_reporter: callable with signature `done_reporter(<NoneInstance>)`
        """
        max_workers = self._get_max_workers(self.configHolder)
        scaler = VmScaler(scale_action, max_workers, self.verboseLevel)
        scaler.set_tasks_and_run(node_instances, done_reporter)
        scaler.wait_tasks_finished()


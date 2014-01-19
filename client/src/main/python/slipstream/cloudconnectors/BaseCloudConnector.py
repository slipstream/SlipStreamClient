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
import os
import time
import tempfile
import random
import string
from threading import local

from slipstream.listeners.SlipStreamClientListenerAdapter import SlipStreamClientListenerAdapter
from slipstream.listeners.SimplePrintListener import SimplePrintListener
from slipstream.Client import Client
from slipstream.util import deprecated
from slipstream import util, SlipStreamHttpClient
from slipstream.utils.ssh import remoteRunScriptNohup, \
    waitUntilSshCanConnectOrTimeout, remoteRunScript, remoteInstallPackages, generateKeyPair
from slipstream.utils.tasksrunner import TasksRunner
from slipstream.NodeDecorator import NodeDecorator
import slipstream.exceptions.Exceptions as Exceptions
from slipstream.wrappers.BaseWrapper import NodeInfoPublisher
from winrm.winrm_service import WinRMWebService
from winrm.exceptions import WinRMTransportError


class BaseCloudConnector(object):
    TIMEOUT_CONNECT = 10 * 60

    DISK_VOLATILE_PARAMETER_NAME = (SlipStreamHttpClient.DomExtractor.EXTRADISK_PREFIX + 
                                    '.volatile')
    DISK_PERSISTENT_PARAMETER_NAME = (SlipStreamHttpClient.DomExtractor.EXTRADISK_PREFIX + 
                                      '.persistent')

    RUN_BOOTSTRAP_SCRIPT = False
    WAIT_IP = False
    ADD_SSHPUBKEY_ON_NODE = False

    # CAPABILITIES
    CAPABILITY_VAPP = 'vapp'
    CAPABILITY_BUILD_IN_SINGLE_VAPP = 'buildInSingleVapp'
    CAPABILITY_CONTEXTUALIZATION = 'contextualization'
    CAPABILITY_WINDOWS_CONTEXTUALIZATION = 'windowsContextualization'
    CAPABILITY_GENERATE_PASSWORD = 'generatePassword'
    CAPABILITY_DIRECT_IP_ASSIGNMENT = 'directIpAssignment'
    CAPABILITY_ADD_SHH_PUBLIC_KEY_ON_NODE = 'addSshPublicKeyOnNode'
    CAPABILITY_ORCHESTRATOR_CAN_KILL_ITSELF_OR_ITS_VAPP = 'orchestratorCanKillItselfOrItsVapp'

    def __init__(self, configHolder):
        self.verboseLevel = 0
        configHolder.assign(self)
        self.configHolder = configHolder

        self.sshPrivKeyFile = '%s/.ssh/id_rsa' % os.path.expanduser("~")
        self.sshPubKeyFile = self.sshPrivKeyFile + '.pub'

        self.listener = SimplePrintListener(verbose=(self.verboseLevel > 1))

        self._vms = {}

        self.cloud = os.environ['SLIPSTREAM_CONNECTOR_INSTANCE']

        # For image creation.
        self._newImageId = ''  # created image ID on a Cloud
        self._creatorVmId = ''  # image ID of creator instance

        self._terminateRunServerSide = False

        self._init_threading_related()

        self.tempPrivateKeyFileName = ''
        self.tempPublicKey = ''

        self._capabilities = []

    def _init_threading_related(self):
        self.tasksRunnner = TasksRunner()

        # This parameter is thread local
        self._thread_local = local()
        self._thread_local.isWindows = False

    def setCapabilities(self, vapp=False, build_in_single_vapp=False,
                        contextualization=False, 
                        windows_contextualization=False,
                        generate_password=False,
                        direct_ip_assignment=False,
                        add_ssh_public_key_on_node=False,
                        orchestrator_can_kill_itself_or_its_vapp=False):
        if vapp:
            self._capabilities.append(self.CAPABILITY_VAPP)
        if build_in_single_vapp:
            self._capabilities.append(self.CAPABILITY_BUILD_IN_SINGLE_VAPP)
        if contextualization:
            self._capabilities.append(self.CAPABILITY_CONTEXTUALIZATION)
        if windows_contextualization:
            self._capabilities.append(self.CAPABILITY_WINDOWS_CONTEXTUALIZATION)
        if generate_password:
            self._capabilities.append(self.CAPABILITY_GENERATE_PASSWORD)
        if direct_ip_assignment:
            self._capabilities.append(self.CAPABILITY_DIRECT_IP_ASSIGNMENT)
        if add_ssh_public_key_on_node:
            self._capabilities.append(self.CAPABILITY_ADD_SHH_PUBLIC_KEY_ON_NODE)
        if orchestrator_can_kill_itself_or_its_vapp:
            self._capabilities.append(self.CAPABILITY_ORCHESTRATOR_CAN_KILL_ITSELF_OR_ITS_VAPP)

    def hasCapability(self, capability):
        return capability in self._capabilities

    @staticmethod
    def extractAllTargets(imageInfo):
        """Return: three tuple of strings (prerecipe, recipe, packages).
        packages - space separated list of packages to install.
        """
        imageTargets = BaseCloudConnector.getTargets(imageInfo)
        prerecipe = imageTargets.get('prerecipe', '').strip()
        recipe = imageTargets.get('recipe', '').strip()
        packages = ' '.join(imageTargets.get('packages', '')).strip()
        return prerecipe, recipe, packages

    @staticmethod
    def getResourceUri(imageInfo):
        return imageInfo['attributes']['resourceUri']

    @staticmethod
    def getAttributes(imageInfo):
        return imageInfo['attributes']

    @staticmethod
    def getImageUser(imageInfo):
        return imageInfo['attributes']['loginUser']

    @staticmethod
    def getCloudParameters(image):
        return image['cloud_parameters']['Cloud']

    @staticmethod
    def getCloudNetworkType(image_info):
        return BaseCloudConnector.getCloudParameters(image_info)['network']

    @staticmethod
    def getTargets(imageInfo):
        return imageInfo['targets']

    @staticmethod
    def _getSshPrivateKey(userInfo):
        return userInfo.get_cloud('private.key')

    @staticmethod
    def getImageId(image_info):
        imageId = image_info['attributes']['imageId']
        if not imageId:
            raise Exceptions.ExecutionException("Couldn't get image ID.")
        return imageId

    @staticmethod
    def setPlatform(imageInfo, platform):
        imageInfo['attributes']['platform'] = platform

    @staticmethod
    def getPlatform(image_info):
        return image_info['attributes']['platform']

    @staticmethod
    def setArchitecture(imageInfo, arch):
        imageInfo['attributes']['arch'] = arch

    @staticmethod
    def getArchitecture(image_info):
        return image_info['attributes']['arch']

    @staticmethod
    def getExtraDisks(image_info):
        return image_info['extra_disks']

    def _userInfoGetKeypairName(self, user_info):
        return user_info.get_cloud('keypair.name')

    def _userInfoSetPrivateKey(self, user_info, privkey):
        user_info[user_info.cloud + 'private.key'] = privkey

    def _userInfoSetKeypairName(self, user_info, kp_name):
        user_info[user_info.cloud + 'keypair.name'] = kp_name

    def isWindows(self):
        return self._thread_local.isWindows

    def _setIsWindows(self, image_info):
        self._thread_local.isWindows = self.getPlatform(image_info).lower() == 'windows'

    @deprecated
    def setRunBootstrapScript(self, run=True):
        self.RUN_BOOTSTRAP_SCRIPT = run

    @deprecated
    def needRunBootstrapScript(self):
        return self.RUN_BOOTSTRAP_SCRIPT is True

    @deprecated
    def setWaitIp(self):
        self.WAIT_IP = True

    @deprecated
    def needWaitIp(self):
        return self.WAIT_IP is True

    @deprecated
    def setNeedToAddSshPubkeyOnNode(self):
        self.ADD_SSHPUBKEY_ON_NODE = True

    @deprecated
    def needToAddSshPubkeyOnNode(self):
        return self.ADD_SSHPUBKEY_ON_NODE

    def startImage(self, user_info, image_info):
        name = NodeDecorator.MACHINE_NAME

        self.initialization(user_info)

        try:
            vm = self._startImage(user_info, image_info, name)
            self.addVm(name, vm)

            self._creatorVmId = self.vmGetId(vm)

            if not self.hasCapability(self.CAPABILITY_DIRECT_IP_ASSIGNMENT):
                vm = self._waitAndGetInstanceIpAddress(vm)
                self.addVm(name, vm)
        finally:
            self.finalization(user_info)

        return self.getVmsDetails()

    def startNodesAndClients(self, user_info, nodes_info):
        self.initialization(user_info)

        try:
            self._startNodeInstantiationTasksWaitFinished(user_info, nodes_info)
        finally:
            self.finalization(user_info)

        return self.getVmsDetails()

    def _startNodeInstantiationTasksWaitFinished(self, user_info, nodes_info):
        for node_info in nodes_info:
            self._startNodeInstancesAndClients(user_info, node_info)

        self._waitNodesStartupTasksFinshed()

    def _startNodeInstancesAndClients(self, user_info, node_info):
        for node_number in range(1, int(node_info['multiplicity']) + 1):
            self.tasksRunnner.run_task(self._startNodeInstanceAndClient,
                                       (user_info, node_info, node_number))

    def _waitNodesStartupTasksFinshed(self):
        self.tasksRunnner.wait_tasks_finished()

    def _startNodeInstanceAndClient(self, user_info, node_info, node_number):
        image_info = self._extractImageInfoFromNodeInfo(node_info)
        nodename = self._generateNodeName(node_info['nodename'], node_number)

        self._setIsWindows(image_info)

        self._printDetail("Starting node: %s" % nodename)

        cloudSpecificData = self._getCloudSpecificData(node_info,
                                                       node_number, nodename)
        vm = self._startImage(user_info,
                              image_info,
                              self._generateInstanceName(nodename),
                              cloudSpecificData)

        self.addVm(nodename, vm)

        if not self.hasCapability(self.CAPABILITY_DIRECT_IP_ASSIGNMENT):
            vm = self._waitAndGetInstanceIpAddress(vm)
            self.addVm(nodename, vm)

        if not self.hasCapability(self.CAPABILITY_CONTEXTUALIZATION) and not self.isWindows():
            self._secureSshAccessAndRunBootstrapScript(user_info, image_info,
                                                       nodename, 
                                                       self.vmGetIp(vm))
        elif not self.hasCapability(self.CAPABILITY_WINDOWS_CONTEXTUALIZATION) and self.isWindows():
            self._launchWindowsBootstrapScript(image_info, nodename,
                                               self.vmGetIp(vm))

    def _startImage(self, user_info, image_info, instance_name, cloudSpecificData=None):
        """Cloud specific VM provisioning.
        Returns: node - cloud specific representation of a started VM."""
        raise NotImplementedError()

    def initialization(self, user_info):
        pass

    def finalization(self, user_info):
        """This method is called once when all instances have been started or
        if an exception has occurred."""
        pass

    def _getCloudSpecificData(self, node_info, node_number, nodename):
        return None

    def _waitAndGetInstanceIpAddress(self, vm):
        """This method needs to be implemented by the connector if the latter
        not define the capability 'direct_ip_assignment'."""
        return vm

    def vmGetIp(self, vm_instance):
        """Cloud specific getter.
        Returns: one IP - Public or Private."""
        raise NotImplementedError()

    def vmGetId(self, vm_instance):
        """Cloud specific getter.
        Returns: cloud ID of the instance."""
        raise NotImplementedError()

    def vmGetPassword(self, vm_name):
        return None

    def stopDeployment(self):
        """This method should terminate all instances except the orchestrator if
        the connector don't has the vapp capability.
        This method should terminate the full vapp if the connector has the vapp
        capability."""
        pass

    # please use stopDeployment instead
    @deprecated
    def stopImages(self):
        """Please use stopDeployment instead"""
        return self.stopDeployment()

    @deprecated
    def stopImagesByIds(self, ids):
        """Please use stopVmsByIds instead"""
        return self.stopVmsByIds(ids)

    def stopVmsByIds(self, ids):
        pass

    def stopVappsByIds(self, ids):
        pass

    @deprecated
    def setTerminateRunServerSide(self):
        self._terminateRunServerSide = True

    @deprecated
    def isTerminateRunServerSide(self):
        return self._terminateRunServerSide

    def addVm(self, name, vm):
        self._vms[name] = vm
        self.publishVmInfo(name, vm)

    def publishVmInfo(self, nodename, vm):
        self.publishVmId(nodename, self.vmGetId(vm))
        self.publishVmIp(nodename, self.vmGetIp(vm))

    def publishVmId(self, nodename, vm_id):
        # Needed for thread safety
        NodeInfoPublisher(self.configHolder).publish_instanceid(nodename, str(vm_id))

    def publishVmIp(self, nodename, vm_ip):
        # Needed for thread safety
        NodeInfoPublisher(self.configHolder).publish_hostname(nodename, vm_ip)

    def getVms(self):
        return self._vms

    def getVm(self, name):
        try:
            return self._vms[name]
        except KeyError:
            raise Exceptions.NotFoundError("VM '%s' not found." % name)

    def _setTempPrivateKeyAndPublicKey(self, privateKeyFileName, publicKey):
        self.tempPrivateKeyFileName = privateKeyFileName
        self.tempPublicKey = publicKey

    def _getTempPrivateKeyFileNameAndPublicKey(self):
        return self.tempPrivateKeyFileName, self.tempPublicKey

    def _buildImage(self, user_info, image_info):
        pass

    def buildImage(self, user_info, image_info):
        if not self.hasCapability(self.CAPABILITY_CONTEXTUALIZATION):
            username, password = self._getSshUsernamePassword(image_info)
            privateKey, publicKey = generateKeyPair()
            privateKey = util.filePutContentInTempFile(privateKey)
            self._setTempPrivateKeyAndPublicKey(privateKey, publicKey)
            ip = self.vmGetIp(self.getVm(NodeDecorator.MACHINE_NAME))
            self._secureSshAccess(ip, username, password, publicKey)

        new_id = self._buildImage(user_info, image_info)
        if new_id:
            self.setNewImageId(new_id)

        return new_id

    def getNewImageId(self):
        return self._newImageId

    def setNewImageId(self, image_id):
        self._newImageId = image_id

    def getCreatorVmId(self):
        return self._creatorVmId

    def _buildImageIncrement(self, user_info, imageInfo, host):
        prerecipe, recipe, packages = self.extractAllTargets(imageInfo)
        try:
            username, password, sshPrivateKeyFile = \
                self._getSshCredentials(imageInfo, user_info,
                                        NodeDecorator.MACHINE_NAME)

            if not self.hasCapability(self.CAPABILITY_CONTEXTUALIZATION) and not sshPrivateKeyFile:
                password = ''
                sshPrivateKeyFile, publicKey = self._getTempPrivateKeyFileNameAndPublicKey()

            self._waitCanConnectWithSshOrAbort(host, username=username,
                                               password=password,
                                               sshKey=sshPrivateKeyFile)

            if prerecipe:
                util.printStep('Running Pre-recipe')
                remoteRunScript(username, host, prerecipe,
                                sshKey=sshPrivateKeyFile, password=password)
            if packages:
                util.printStep('Installing Packages')
                remoteInstallPackages(username, host, packages,
                                      self.getPlatform(imageInfo),
                                      sshKey=sshPrivateKeyFile, password=password)
            if recipe:
                util.printStep('Running Recipe')
                remoteRunScript(username, host, recipe,
                                sshKey=sshPrivateKeyFile, password=password)

            if not self.hasCapability(self.CAPABILITY_CONTEXTUALIZATION):
                self._revertSshSecurity(host, username, sshPrivateKeyFile, publicKey)
        finally:
            try:
                os.unlink(sshPrivateKeyFile)
            except:
                pass

    def _getCloudInstanceName(self):
        return self.cloud
    
    def _getSshCredentials(self, imageInfo, user_info, vm_name=None):
        username, password = self._getSshUsernamePassword(imageInfo, vm_name)
        if password:
            sshPrivateKeyFile = None
        else:
            sshPrivateKeyFile = self._getSshPrivateKeyFile(user_info)
        return username, password, sshPrivateKeyFile

    def _getSshPrivateKeyFile(self, user_info):
        fd, sshPrivateKeyFile = tempfile.mkstemp()
        os.write(fd, self._getSshPrivateKey(user_info))
        os.close(fd)
        os.chmod(sshPrivateKeyFile, 0400)
        return sshPrivateKeyFile

    def _getInstanceType(self, image):
        return self._getCloudParameter(image, 'instance.type')

    def _getImageCpu(self, image):
        return self._getCloudParameter(image, 'cpu')

    def _getImageRam(self, image):
        return self._getCloudParameter(image, 'ram')

    def _getImageSmp(self, image):
        return self._getCloudParameter(image, 'smp')

    def _getImageNetworkType(self, image):
        return self._getCloudParameter(image, 'network')

    def _getSshUsernamePassword(self, image, vm_name=None):
        attributes = image['attributes']

        user = attributes.get('loginUser', '')
        if not user:
            user = 'root'
        password = None
        try:
            password = self._getCloudParameter(image, 'login.password')
        except Exceptions.ParameterNotFoundException:
            try:
                password = self.vmGetPassword(vm_name)
            except:
                pass
        return user, password

    def _getCloudParameter(self, image, parameter):
        params = image['cloud_parameters'][self.cloud]
        param = '%s.%s' % (self.cloud, parameter)
        try:
            return params[param]
        except KeyError:
            raise Exceptions.ParameterNotFoundException("Cloud parameter '%s' not found" % param)

    def _generateNodeName(self, nodename, node_number):
        return nodename + NodeDecorator.NODE_MULTIPLICITY_SEPARATOR + str(node_number)

    def _generateInstanceName(self, nodename):
        return nodename + ':%s' % self._getRunId()

    def _getRunId(self):
        return os.environ.get('SLIPSTREAM_DIID', '???')

    def _secureSshAccessAndRunBootstrapScript(self, userInfo, image_info, nodename, ip):
        username, password = self._getSshUsernamePassword(image_info, nodename)
        privateKey, publicKey = generateKeyPair()
        privateKey = util.filePutContentInTempFile(privateKey)

        self._secureSshAccess(ip, username, password, publicKey, userInfo)
        self._launchBootstrapScript(nodename, ip, username, privateKey)

    def _secureSshAccess(self, ip, username, password, publicKey, userInfo=None):
        self._waitCanConnectWithSshOrAbort(ip, username, password)
        script = self.getObfuscationScript(publicKey, username, userInfo)
        self._printDetail("Securing SSH access to %s with:\n%s\n" % (ip, script))
        _, output = self._runScript(ip, username, script, password=password)
        self._printDetail("Secured SSH access to %s. Output:\n%s\n" % (ip, output))

    def _revertSshSecurity(self, ip, username, privateKey, orchestratorPublicKey):
        self._waitCanConnectWithSshOrAbort(ip, username, sshKey=privateKey)
        script = "#!/bin/bash -xe\n"
        script += "set +e\n"
        script += "grep -vF '" + orchestratorPublicKey + "' ~/.ssh/authorized_keys > ~/.ssh/authorized_keys.tmp\n"
        script += "set -e\n"
        script += "sleep 2\nmv ~/.ssh/authorized_keys.tmp ~/.ssh/authorized_keys\n"
        script += "chown -R " + username + ":$(id -g " + username + ")" + " ~/.ssh\n"
        script += "restorecon -Rv ~/.ssh || true\n"
        script += "sed -i -r 's/^#?[\\t ]*(PasswordAuthentication[\\t ]+)((yes)|(no))/\\1yes/' /etc/ssh/sshd_config\n"
        script += "sync\nsleep 2\n"
        script += "[ -x /etc/init.d/sshd ] && { service sshd reload; } || { service ssh reload; }\n"
        self._printDetail("Reverting security of SSH access to %s with:\n%s\n" % (ip, script))
        _, output = self._runScript(ip, username, script, sshKey=privateKey)
        self._printDetail("Reverted security of SSH access to %s. Output:\n%s\n" % (ip, output))

    def _launchBootstrapScript(self, nodename, ip, username, privateKey):
        self._waitCanConnectWithSshOrAbort(ip, username, sshKey=privateKey)
        script = self._getBootstrapScript(nodename)
        self._printDetail("Launching bootstrap script on %s:\n%s\n" % (ip, script))
        _, output = self._runScriptOnBackgroud(ip, username, script, sshKey=privateKey)
        self._printDetail("Launched bootstrap script on %s:\n%s\n" % (ip, output))

    def _launchWindowsBootstrapScript(self, image_info, nodename, ip):
        username, password = self._getSshUsernamePassword(image_info, nodename)
        script = self._getBootstrapScript(nodename, username=username)
        winrm = self._getWinrm(ip, username, password)
        self._waitCanConnectWithWinrmOrAbort(winrm)
        self._printDetail("Launching bootstrap script on %s:\n%s\n" % (ip, script))
        util.printAndFlush(script)
        winrm.timeout = winrm.set_timeout(600)
        output = self._runScriptWithWinrm(winrm, script)
        self._printDetail("Launched bootstrap script on %s:\n%s\n" % (ip, output))

    def _getWinrm(self, ip, username, password):
        return WinRMWebService(endpoint='http://%s:5985/wsman' % ip, transport='plaintext', 
                               username=username, password=password)

    def _runScriptWithWinrm(self, winrm, script):
        shellId = winrm.open_shell()
        commands = ''
        for command in script.splitlines():
            if command:
                commands += command + '& '
        commands += 'echo "Bootstrap Finished"'
        stdout, stderr, returnCode = self._runCommandWithWinrm(winrm, commands, shellId, 
                                                               runAndContinue=True)
        #winrm.close_shell(shellId)
        return stdout, stderr, returnCode

    def _waitCanConnectWithWinrmOrAbort(self, winrm):
        try:
            self._waitCanConnectWithWinrmOrTimeout(winrm, self.TIMEOUT_CONNECT)
        except Exception as ex:
            raise Exceptions.ExecutionException("Failed to connect to %s: %s" % (winrm.endpoint, 
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

    def _runCommandWithWinrm(self, winrm, command, shellId=None, runAndContinue=False):
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
            except Exception as e:
                print 'WINRM Exception: %s' % str(e)
        util.printAndFlush('\nwinrm.cleanup_command\n')
        if not runAndContinue:
            winrm.cleanup_command(_shellId, commandId)
            if not shellId:
                winrm.close_shell(_shellId)
        return stdout, stderr, returnCode

    def getObfuscationScript(self, orchestratorPublicKey, username, userInfo=None):
        command = "#!/bin/bash -xe\n"
        #command += "sed -r -i 's/# *(account +required +pam_access\\.so).*/\\1/' /etc/pam.d/login\n"
        #command += "echo '-:ALL:LOCAL' >> /etc/security/access.conf\n"
        command += "sed -i -r '/^[\\t ]*RSAAuthentication/d;/^[\\t ]*PubkeyAuthentication/d;/^[\\t ]*PasswordAuthentication/d' /etc/ssh/sshd_config\n"
        command += "echo 'RSAAuthentication yes\nPubkeyAuthentication yes\nPasswordAuthentication no\n' >> /etc/ssh/sshd_config\n"
        #command += "sed -i -r 's/^#?[\\t ]*(RSAAuthentication[\\t ]+)((yes)|(no))/\\1yes/' /etc/ssh/sshd_config\n"
        #command += "sed -i -r 's/^#?[\\t ]*(PubkeyAuthentication[\\t ]+)((yes)|(no))/\\1yes/' /etc/ssh/sshd_config\n"
        #command += "sed -i -r 's/^#?[\t ]*(PasswordAuthentication[\\t ]+)((yes)|(no))/\\1no/' /etc/ssh/sshd_config\n"
        command += "umask 077\n"
        command += "mkdir -p ~/.ssh\n"
        if userInfo:
            command += "echo '" + self._getPublicSshKey(userInfo) + "' >> ~/.ssh/authorized_keys\n"
        command += "echo '" + orchestratorPublicKey + "' >> ~/.ssh/authorized_keys\n"
        command += "chown -R " + username + ":$(id -g " + username + ")" + " ~/.ssh\n"
        command += "restorecon -Rv ~/.ssh || true\n"
        command += "[ -x /etc/init.d/sshd ] && { service sshd reload; } || { service ssh reload; }\n"
        return command

    def _getPublicSshKey(self, userInfo):
        return userInfo.get_general('ssh.public.key') or ''

    def _getBootstrapScript(self, nodename, preExport=None, preBootstrap=None, postBootstrap=None, 
                            username=None):
        script = ''
        addEnvironmentVariableCommand = ''
        if self.isWindows():
            addEnvironmentVariableCommand = 'set'
        else:
            addEnvironmentVariableCommand = 'export'
            script += '#!/bin/sh -ex\n'

        if preExport:
            script += '%s\n' % preExport
        util.printAndFlush(str(os.environ))

        for var, val in os.environ.items():
            if var.startswith('SLIPSTREAM_') and var != 'SLIPSTREAM_NODENAME':
                if var == 'SLIPSTREAM_REPORT_DIR' and self.isWindows():
                    val = Client.WINDOWS_REPORTSDIR
                if re.search(' ', val):
                    val = '"%s"' % val
                script += '%s %s=%s\n' % (addEnvironmentVariableCommand, var, val)

        script += '%s SLIPSTREAM_NODENAME=%s\n' % (addEnvironmentVariableCommand, nodename)

        script += '%s %s=%s\n' % (addEnvironmentVariableCommand,
                                  util.ENV_NEED_TO_ADD_SSHPUBKEY,
                                  self.hasCapability(self.ADD_SSHPUBKEY_ON_NODE))

        if preBootstrap:
            script += '%s\n' % preBootstrap

        script += '%s\n' % self._buildSlipStreamBootstrapCommand(nodename, username)

        if postBootstrap:
            script += '%s\n' % postBootstrap

        return script

    def _buildSlipStreamBootstrapCommand(self, nodename, username=None):
        if self.isWindows():
            return self._buildSlipStreamBootstrapCommandForWindows(nodename, username)
        else:
            return self._buildSlipStreamBootstrapCommandForLinux(nodename)

    def _buildSlipStreamBootstrapCommandForWindows(self, nodename, username):
        if not username:
            username = 'administrator'
        bootstrap = 'slipstream.bootstrap'
        reportdir = Client.WINDOWS_REPORTSDIR
        command = 'mkdir %(reports)s\n'
        command += 'powershell -Command "$wc = New-Object System.Net.WebClient; $wc.DownloadFile(\'http://www.python.org/ftp/python/2.7.4/python-2.7.4.msi\', $env:temp+\'\\python.msi\')"\n'
        command += 'start /wait msiexec /i %%TMP%%\\python.msi /qn /quiet /norestart /log log.txt TARGETDIR=C:\\Python27\\ ALLUSERS=1\n'
        command += 'setx path "%%path%%;C:\\Python27" /M\n'
        command += 'powershell -Command "[System.Net.ServicePointManager]::ServerCertificateValidationCallback = {$true}; $wc = New-Object System.Net.WebClient; $wc.Headers.Add(\'User-Agent\',\'PowerShell\'); $wc.DownloadFile(\'%(bootstrapUrl)s\', $env:temp+\'\\%(bootstrap)s\')" > %(reports)s\\%(nodename)s.slipstream.log 2>&1\n'
        command += 'set PATH=%%PATH%%;C:\\Python27;C:\\opt\\slipstream\\client\\bin\n'
        command += 'set PYTHONPATH=C:\\opt\\slipstream\\client\\lib\n'
        
        password = ''
        if not self.hasCapability(self.CAPABILITY_GENERATE_PASSWORD):
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

        #command += 'C:\\Python27\\python %%TMP%%\\%(bootstrap)s >> %(reports)s\%(nodename)s.slipstream.log 2>&1\n'
        command += 'start "test" "%%SystemRoot%%\System32\cmd.exe" /C "C:\\Python27\\python %%TMP%%\\%(bootstrap)s >> %(reports)s\%(nodename)s.slipstream.log 2>&1"\n'
        return command % {
            'bootstrap': bootstrap,
            'bootstrapUrl': os.environ['SLIPSTREAM_BOOTSTRAP_BIN'],
            'reports': reportdir,
            'nodename': nodename,
            'username': username,
            'password': password
        }

    def _buildSlipStreamBootstrapCommandForLinux(self, nodename):
        bootstrap = os.path.join(tempfile.gettempdir(), 'slipstream.bootstrap')
        reportdir = Client.REPORTSDIR
        command = 'mkdir -p %(reports)s; wget --no-check-certificate --secure-protocol=SSLv3 -O %(bootstrap)s %(bootstrapUrl)s >%(reports)s/%(nodename)s.slipstream.log 2>&1 && chmod 0755 %(bootstrap)s; %(bootstrap)s >>%(reports)s/%(nodename)s.slipstream.log 2>&1'
        return command % {
            'bootstrap': bootstrap,
            'bootstrapUrl': os.environ['SLIPSTREAM_BOOTSTRAP_BIN'],
            'reports': reportdir,
            'nodename': nodename
        }

    def _waitCanConnectWithSshOrAbort(self, host, username='', password='', sshKey=None):
        self._printDetail('Check if we can connect to %s' % host)
        try:
            waitUntilSshCanConnectOrTimeout(host,
                                            self.TIMEOUT_CONNECT,
                                            sshKey=sshKey,
                                            user=username, password=password)
        except Exception as ex:
            raise Exceptions.ExecutionException("Failed to connect to %s: %s" % (host, str(ex)))

    def _runScript(self, ip, username, script, password='', sshKey=None):
        return remoteRunScript(username, ip, script, sshKey=sshKey,
                               password=password)

    def _runScriptOnBackgroud(self, ip, username, script, password='', sshKey=None):
        return remoteRunScriptNohup(username, ip, script,
                                    sshKey=sshKey, password=password)

    def _extractImageInfoFromNodeInfo(self, node_info):
        return node_info['image']

    def setSlipStreamClientAsListener(self, client):
        self.listener = SlipStreamClientListenerAdapter(client)

    def _printDetail(self, message):
        util.printDetail(message, self.verboseLevel)

    def getVmsDetails(self):
        vms_details = []
        for name, vm in self.getVms().items():
            vms_details.append({name: {'id': self.vmGetId(vm),
                                       'ip': self.vmGetIp(vm)}})
        return vms_details

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

import base64
import commands
import os
import socket
import time

from stratuslab.ConfigHolder import ConfigHolder as StratuslabConfigHolder
from stratuslab.marketplace.ManifestDownloader import ManifestDownloader
from stratuslab.Creator import Creator
from stratuslab.Creator import CreatorBaseListener
from stratuslab.vm_manager.Runner import Runner
from stratuslab.volume_manager.volume_manager_factory import VolumeManagerFactory

from slipstream.cloudconnectors.BaseCloudConnector import BaseCloudConnector
import slipstream.exceptions.Exceptions as Exceptions
import slipstream.util as util
from slipstream.utils.ssh import generateSshKeyPair


def getConnector(configHolder):
    return getConnectorClass()(configHolder)


def getConnectorClass():
    return StratuslabClientCloud


class StratuslabClientCloud(BaseCloudConnector):
    RUNINSTANCE_RETRY_TIMEOUT = 3

    cloudName = 'stratuslab'

    def __init__(self, slipstreamConfigHolder):
        super(StratuslabClientCloud, self).__init__(slipstreamConfigHolder)

        self.slConfigHolder = StratuslabConfigHolder(slipstreamConfigHolder.options,
                                                     slipstreamConfigHolder.config)

        self.listener = CreatorBaseListener(verbose=(self.verboseLevel > 1))

    def startImage(self, user_info, image_info):
        return self.getVmsDetails()

    def _buildImage(self, userInfo, imageInfo):

        self._prepareMachineForBuildImage()

        self.slConfigHolder.set('marketplaceEndpoint',
                                userInfo.get_cloud('marketplace.endpoint'))

        manifestDownloader = ManifestDownloader(self.slConfigHolder)

        imageId = self.getImageId(imageInfo)
        imageInfo['imageVersion'] = manifestDownloader.getImageVersion(imageId=imageId)

        self._updateStratuslabConfigHolderForBuildImage(userInfo, imageInfo)

        creator = Creator(imageId, self.slConfigHolder)
        creator.setListener(self.listener)

        createImageTemplateDict = creator._getCreateImageTemplateDict()
        msgData = StratuslabClientCloud._getCreateImageTemplateMessaging(imageInfo)

        def ourCreateTemplateDict():
            createImageTemplateDict.update(msgData)
            return createImageTemplateDict

        creator._getCreateImageTemplateDict = ourCreateTemplateDict

        creator.create()

        # 
        # if messaging is set to 'pdisk', then try polling for the new image
        # identifier from the storage system; otherwise will just return empty
        # string
        #
        self._newImageId = self._pollStorageForNewImage(self.slConfigHolder)

    def _pollStorageForNewImage(self, slConfigHolder):

        newImageId = ''

        msg_type = os.environ.get('SLIPSTREAM_MESSAGING_TYPE', None)
        msg_endpoint = os.environ.get('SLIPSTREAM_MESSAGING_ENDPOINT', None)

        if msg_type and msg_endpoint:
            if msg_type == 'pdisk':

                diid = "SlipStream-%s" % os.environ.get('SLIPSTREAM_DIID', None)
                if diid:
                    tag = "SlipStream-%s" % diid
                    filters = {'tag': [tag,]}

                    slConfigHolder.set('pdiskEndpoint', msg_endpoint)

                    pdisk = VolumeManagerFactory.create(slConfigHolder)

                    print "Searching on %s for disk with tag %s." % (msg_endpoint, tag)

                    # hardcoded polling for 30' at 1' intervals
                    for i in range(30):
                        print "Search iteration %d" % i
                        volumes = pdisk.describeVolumes(filters)
                        if len(volumes) > 0:
                            try:
                                newImageId = volumes[0]['identifier']
                            except Exception as e:
                                print "Exception occurred looking for volume: %s" % e
                                pass
                            break;
                        time.sleep(60)

        print "Returning new image ID value: " % newImageId
        return newImageId

    @staticmethod
    def _getCreateImageTemplateMessaging(imageInfo):
        msg_type = os.environ.get('SLIPSTREAM_MESSAGING_TYPE', None)

        if msg_type:
            imageResourceUri = BaseCloudConnector.getResourceUri(imageInfo) + '/stratuslab'
            message = StratuslabClientCloud._getCreateImageMessagingMessage(imageResourceUri)
            msgData = {Runner.CREATE_IMAGE_KEY_MSG_TYPE: msg_type,
                       Runner.CREATE_IMAGE_KEY_MSG_ENDPOINT: os.environ['SLIPSTREAM_MESSAGING_ENDPOINT'],
                       Runner.CREATE_IMAGE_KEY_MSG_MESSAGE: message}
            if msg_type in ('amazonsqs', 'dirq'):
                msgData.update({Runner.CREATE_IMAGE_KEY_MSG_QUEUE: os.environ['SLIPSTREAM_MESSAGING_QUEUE']})
            elif msg_type == 'rest':
                msgData.update({Runner.CREATE_IMAGE_KEY_MSG_QUEUE: imageResourceUri})
            elif msg_type == 'pdisk':
                msgData = {}
            else:
                raise Exceptions.ExecutionException('Unsupported messaging type: %s' % msg_type)
        else:
            msgData = {}
        return msgData

    @staticmethod
    def _getCreateImageMessagingMessage(imageResourceUri):
        return base64.b64encode('{"uri":"%s", "imageid":""}' % imageResourceUri)

    def initialization(self, user_info):
        self.slConfigHolder.options.update(Runner.defaultRunOptions())
        self._setUserInfoOnStratuslabConfigHolder(user_info)

    def _startImage(self, user_info, image_info, instance_name, cloudSpecificData=None):
        configHolder = self.slConfigHolder.deepcopy()

        self._setInstanceParamsOnConfigHolder(configHolder, image_info)

        imageId = self.getImageId(image_info)

        self._setExtraContextDataOnConfigHolder(configHolder, cloudSpecificData)
        self._setVmNameOnConfigHolder(configHolder, instance_name)

        runner = self._runInstance(imageId, configHolder)

        return runner

    def _getCloudSpecificData(self, node_info, node_number, nodename):
        return nodename

    def vmGetIp(self, runner):
        return runner.instancesDetail[0]['ip']

    def vmGetId(self, runner):
        return runner.instancesDetail[0]['id']

    def _setInstanceParamsOnConfigHolder(self, configHolder, image):
        self._setInstanceSizeOnConfigHolder(configHolder, image)
        self._setExtraDisksOnConfigHolder(configHolder, image)
        self._setNetworkTypeOnConfigHolder(configHolder, image)

    def _setInstanceSizeOnConfigHolder(self, configHolder, image):
        self._setInstanceTypeOnConfigHolder(configHolder, image)
        self._setCpuRamOnConfigHolder(configHolder, image)

    def _setInstanceTypeOnConfigHolder(self, configHolder, image):
        configHolder.instanceType = self._getInstanceType(image)

    def _setCpuRamOnConfigHolder(self, configHolder, image):
        configHolder.vmCpu = self._getImageCpu(image) or None
        vmRamGb = self._getImageRam(image) or None
        if vmRamGb:
            try:
                # StratusLab needs value in MB
                configHolder.vmRam = str(int(vmRamGb.strip()) * 1024)
            except:
                pass

    def _setExtraDisksOnConfigHolder(self, configHolder, image):
        extra_disks = self.getExtraDisks(image)
        # 'extra_disk_volatile' is given in GB - 'extraDiskSize' needs to be in MB
        configHolder.extraDiskSize = int(extra_disks.get('extra.disk.volatile', 0) or 0) * 1024
        configHolder.persistentDiskUUID = extra_disks.get('extra_disk_persistent', '')
        configHolder.readonlyDiskId = extra_disks.get('extra_disk_readonly', '')

    def _setExtraContextDataOnConfigHolder(self, configHolder, nodename):
        configHolder.extraContextData = '#'.join(
            ['%s=%s' % (k, v) for (k, v) in os.environ.items() if k.startswith('SLIPSTREAM_')])
        configHolder.extraContextData += '#SLIPSTREAM_NODENAME=%s' % nodename
        configHolder.extraContextData += '#SCRIPT_EXEC=%s' % self._buildSlipStreamBootstrapCommand(nodename)

    def _setVmNameOnConfigHolder(self, configHolder, nodename):
        configHolder.vmName = nodename

    def _runInstance(self, imageId, configHolder, max_attempts=3):
        if max_attempts <= 0:
            max_attempts = 1
        attempt = 1
        while True:
            try:
                runner = self._doRunInstance(imageId, configHolder)
            except socket.error, ex:
                if attempt >= max_attempts:
                    raise Exceptions.ExecutionException(
                        "Failed to launch instance after %i attempts: %s" %
                        (attempt, str(ex)))
                time.sleep(self.RUNINSTANCE_RETRY_TIMEOUT)
                attempt += 1
            else:
                return runner

    def _doRunInstance(self, imageId, configHolder):
        runner = self._getStratusLabRunner(imageId, configHolder)
        runner.runInstance()
        return runner

    def _getStratusLabRunner(self, imageId, configHolder):
        return Runner(imageId, configHolder)

    def _prepareMachineForBuildImage(self):
        generateSshKeyPair(self.sshPrivKeyFile)
        self._installPackagesLocal(['curl'])

    @staticmethod
    def _installPackagesLocal(packages):
        cmd = 'apt-get -y install %s' % ' '.join(packages)
        rc, output = commands.getstatusoutput(cmd)
        if rc != 0:
            raise Exceptions.ExecutionException('Could not install required packages: %s\n%s' % (cmd, output))
            # FIXME: ConfigHolder needs more info for a proper bootstrap. Substitute later.
        #            machine = SystemFactory.getSystem('ubuntu', self.slConfigHolder)
        #            machine.installPackages(packages)

    def _buildSlipStreamBootstrapCommand(self, nodename):
        return "sleep 15; " + \
               super(StratuslabClientCloud, self)._buildSlipStreamBootstrapCommand(nodename)

    def stopImages(self):
        errors = []
        for nodename, runner in self.getVms().items():
            try:
                runner.killInstances()
            except Exception, ex:
                errors.append('Error killing node %s\n%s' % (nodename, ex.message))
        if errors:
            raise Exceptions.CloudError('Failed stopping following instances. Details: %s' % '\n   -> '.join(errors))

    def stopImagesByIds(self, ids):
        configHolder = self.slConfigHolder.copy()
        runner = Runner(None, configHolder)
        runner.killInstances(map(int, ids))

    def _updateStratuslabConfigHolderForBuildImage(self, userInfo, imageInfo):

        self.slConfigHolder.set('verboseLevel', self.verboseLevel)

        self.slConfigHolder.set('comment', '')

        title = "SlipStream-%s" % os.environ.get('SLIPSTREAM_DIID', 'undefined diid')
        self.slConfigHolder.set('title', title)

        self._setUserInfoOnStratuslabConfigHolder(userInfo, buildImage=True)
        self._setImageInfoOnStratuslabConfigHolder(imageInfo)

        self._setInstanceSizeOnConfigHolder(self.slConfigHolder, imageInfo)

    def _setImageInfoOnStratuslabConfigHolder(self, buildAndImageInfo):
        self._setBuildTargetsOnStratuslabConfigHolder(buildAndImageInfo)
        self._setNewImageGroupVersionOnStratuslabConfigHolder(buildAndImageInfo)

    def _setBuildTargetsOnStratuslabConfigHolder(self, buildAndImageInfo):
        for target in ['prerecipe', 'recipe']:
            self.slConfigHolder.set(target, buildAndImageInfo['targets'][target] or '')

        packages = ','.join(buildAndImageInfo['targets']['packages'])
        self.slConfigHolder.set('packages', packages)

    def _setNewImageGroupVersionOnStratuslabConfigHolder(self, buildAndImageInfo):
        def _incrementMinorVersionNumber(version):
            try:
                x, y = version.split('.')
                return '.'.join([x, str(int(y) + 1)])
            except:
                return version

        newVersion = _incrementMinorVersionNumber(buildAndImageInfo['imageVersion'])
        self.slConfigHolder.set('newImageGroupVersion', newVersion)
        self.slConfigHolder.set('newImageGroupVersionWithManifestId', True)

    def _setUserInfoOnStratuslabConfigHolder(self, userInfo, buildImage=False):
        try:
            if buildImage:
                self.slConfigHolder.set('author',
                                        '%s %s' % (userInfo.get_user('firstName'),
                                                   userInfo.get_user('lastName')))
                self.slConfigHolder.set('authorEmail',
                                        userInfo.get_user('email'))
                self.slConfigHolder.set('saveDisk', True)

            sshPubKeysFile = self.__populateSshPubKeysFile(userInfo)
            self.slConfigHolder.set('userPublicKeyFile', sshPubKeysFile)

            self.slConfigHolder.set('endpoint', userInfo.get_cloud('endpoint'))
            self.slConfigHolder.set('username', userInfo.get_cloud('username'))
            self.slConfigHolder.set('password', userInfo.get_cloud('password'))

            self.slConfigHolder.set('marketplaceEndpoint',
                                    userInfo.get_cloud('marketplace.endpoint'))
        except KeyError, ex:
            raise Exceptions.ExecutionException('Error bootstrapping from User Parameters. %s' % str(ex))

        #        onErrorRunForever = userInfo.get_global('On Error Run Forever', 'off')
        #        if onErrorRunForever == 'on':
        #            shutdownVm = False
        #        else:
        #            shutdownVm = True
        # To be able to create a new image we need to shutdown the instance.
        shutdownVm = True
        self.slConfigHolder.set('shutdownVm', shutdownVm)

    def _setNetworkTypeOnConfigHolder(self, configHolder, image_info):
        # SS's 'Private' maps to 'local' in SL. The default is 'public' in SL.
        # We don't use SL's 'private' IPs.
        if 'Private' == self.getCloudNetworkType(image_info):
            configHolder.set('isLocalIp', True)

    def __populateSshPubKeysFile(self, userInfo):
        sshPubKeyFileTemp = self.sshPubKeyFile + '.temp'

        try:
            sshPubKeyLocal = util.fileGetContent(self.sshPubKeyFile)
        except:
            sshPubKeyLocal = ''

        userSshPubKey = userInfo.get_general('ssh.public.key')

        sshPubKeys = ''
        for sshKey in [sshPubKeyLocal, userSshPubKey]:
            if sshKey:
                sshPubKeys += '%s\n' % sshKey.strip()

        util.filePutContent(sshPubKeyFileTemp, sshPubKeys)

        return sshPubKeyFileTemp

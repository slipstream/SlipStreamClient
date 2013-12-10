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

import os
import re
import time

from libcloud.compute.types import Provider
from libcloud.compute.types import NodeState
from libcloud.compute.providers import get_driver
import libcloud.security

from slipstream.cloudconnectors.BaseCloudConnector import BaseCloudConnector
from slipstream.NodeDecorator import NodeDecorator, RUN_CATEGORY_IMAGE, \
    RUN_CATEGORY_DEPLOYMENT, KEY_RUN_CATEGORY
import slipstream.util as util
import slipstream.exceptions.Exceptions as Exceptions
from slipstream.cloudconnectors.openstack.libcloudPatch import patchLibcloud


def getConnector(configHolder):
    return getConnectorClass()(configHolder)


def getConnectorClass():
    return OpenStackClientCloud


class OpenStackClientCloud(BaseCloudConnector):
    cloudName = 'openstack'

    def __init__(self, configHolder):
        self.setWaitIp()

        self.run_category = getattr(configHolder, KEY_RUN_CATEGORY)

        patchLibcloud()
        libcloud.security.VERIFY_SSL_CERT = False

        super(OpenStackClientCloud, self).__init__(configHolder)
        
        self.setCapabilities(contextualization=True,
                             orchestrator_can_kill_itself_or_its_vapp=True)

    def initialization(self, user_info):
        util.printStep('Initialize the OpenStack connector.')
        self._thread_local.driver = self._getDriver(user_info)
        self.flavors = self._thread_local.driver.list_sizes()
        self.images = self._thread_local.driver.list_images()
        
        if self.run_category == RUN_CATEGORY_DEPLOYMENT:
            self._importKeypair(user_info)
        elif self.run_category == RUN_CATEGORY_IMAGE:
            self._createKeypairAndSetOnUserInfo(user_info)

    def finalization(self, user_info):
        try:
            kp_name = self._userInfoGetKeypairName(user_info)
            self._deleteKeypair(kp_name)
        except:
            pass

    def _buildImage(self, userInfo, imageInfo):
        self._buildImageOnOpenStack(userInfo, imageInfo)

    def _buildImageOnOpenStack(self, userInfo, imageInfo):
        self._thread_local.driver = self._getDriver(userInfo)

        vm = self.getVm(NodeDecorator.MACHINE_NAME)

        util.printAndFlush("\n  imageInfo: %s \n" % str(imageInfo))
        util.printAndFlush("\n  VM: %s \n" % str(vm))

        ipAddress = self.vmGetIp(vm)
        self._creatorVmId = self.vmGetId(vm)
        instance = vm['instance']

        self._waitInstanceInRunningState(self._creatorVmId)

        self._buildImageIncrement(userInfo, imageInfo, ipAddress)

        attributes = self.getAttributes(imageInfo)

        util.printStep('Creation of the new Image.')
        newImg = self._thread_local.driver.ex_save_image(instance, attributes['shortName'], metadata=None)

        self._waitImageCreationCompleted(newImg.id)

        self._newImageId = newImg.id

    def _startImage(self, user_info, image_info, instance_name, cloudSpecificData=None):
        self._thread_local.driver = self._getDriver(user_info)
        return self._startImageOnOpenStack(user_info, image_info, instance_name, cloudSpecificData)

    def _startImageOnOpenStack(self, user_info, image_info, instance_name, cloudSpecificData=None):
        imageId = self.getImageId(image_info)
        instanceType = self._getInstanceType(image_info)
        keypair = self._userInfoGetKeypairName(user_info)
        securityGroups = [x.strip() for x in self._getCloudParameter(image_info, 'security.groups').split(',') if x]
        flavor = self._searchInObjectList(self.flavors, 'name', instanceType)
        image = self._searchInObjectList(self.images, 'id', imageId)
        contextualizationScript = cloudSpecificData or ''

        if flavor == None: raise Exceptions.ParameterNotFoundException("Couldn't find the specified flavor: %s" % instanceType)
        if image == None: raise Exceptions.ParameterNotFoundException("Couldn't find the specified image: %s" % imageId)

        instance = self._thread_local.driver.create_node(name=instance_name,
                                                         size=flavor,
                                                         image=image,
                                                         ex_keyname=keypair,
                                                         ex_userdata=contextualizationScript,
                                                         ex_security_groups=securityGroups)

        vm = dict(networkType=self.getCloudParameters(image_info)['network'],
                  instance=instance,
                  ip='',
                  id=instance.id)
        return vm

    def _getCloudSpecificData(self, node_info, node_number, nodename):
        return self._getBootstrapScript(nodename)

    def stopDeployment(self):
        for _, vm in self.getVms().items():
            vm['instance'].destroy()

    def stopVmsByIds(self, ids):
        for node in self._thread_local.driver.list_nodes():
            if node.id in ids:
                node.destroy()

    def _getDriver(self, userInfo):
        #if self.driver == None:
        OpenStack = get_driver(Provider.OPENSTACK)
        isHttps = userInfo.get_cloud('endpoint').lower().startswith('https://')

        return OpenStack(userInfo.get_cloud('username'),
                         userInfo.get_cloud('password'),
                         secure=isHttps,
                         ex_tenant_name=userInfo.get_cloud('tenant.name'),
                         ex_force_auth_url=userInfo.get_cloud('endpoint'),
                         ex_force_auth_version='2.0_password',
                         ex_force_service_type=os.environ['OPENSTACK_SERVICE_TYPE'],
                         ex_force_service_name=os.environ['OPENSTACK_SERVICE_NAME'],
                         ex_force_service_region=os.environ['OPENSTACK_SERVICE_REGION'])

    def _searchInObjectList(self, list_, propertyName, propertyValue):
        for element in list_:
            if isinstance(element, dict):
                if element.get(propertyName) == propertyValue:
                    return element
            else:
                if getattr(element, propertyName) == propertyValue:
                    return element
        return None

    def vmGetIp(self, vm):
        return vm['ip']

    def vmGetId(self, vm):
        return vm['id']

    # This is a trick because HPcloud put public IP in private IPs list.
    def _extractPublicPrivateIps(self, instance):
        ips = instance.private_ip + instance.public_ip
        instance.private_ip = []
        instance.public_ip = []

        for ip in ips:
            if re.match(
                    '(10(\.[0-9]{1,3}){3})|(172\.((1[6-9])|(2[0-9])|(3[0-1]))(\.[0-9]{1,3}){2})|(192.168(\.[0-9]{1,3}){2})',
                    ip) != None:
                instance.private_ip.append(ip)
            else:
                instance.public_ip.append(ip)

        return instance

    def _getInstanceIpAddress(self, instance, ipType):
        """ipType - string"""
        instance = self._extractPublicPrivateIps(instance)
        if ipType.lower() == 'private':
            return (len(instance.private_ip) != 0) and instance.private_ip[0] or ''
        else:
            return (len(instance.public_ip) != 0) and instance.public_ip[0] or ''

    def _waitAndGetInstanceIpAddress(self, vm):
        timeWait = 120
        timeStop = time.time() + timeWait

        while time.time() < timeStop:
            time.sleep(1)

            ipType = vm['networkType']
            vmId = vm['id']

            instances = self._thread_local.driver.list_nodes()
            instance = self._searchInObjectList(instances, 'id', vmId)
            ip = self._getInstanceIpAddress(instance, ipType or '')
            if ip:
                vm['ip'] = ip
                return vm

        raise Exceptions.ExecutionException('Timed out while waiting for IPs to be assigned to instances: %s' % vmId)

    def _waitInstanceInRunningState(self, instanceId):
        timeWait = 120
        timeStop = time.time() + timeWait

        state = ''
        while state != NodeState.RUNNING:
            if time.time() > timeStop:
                raise Exceptions.ExecutionException(
                    'Timed out while waiting for instance "%s" enter in running state' % instanceId)
            time.sleep(1)
            node = self._thread_local.driver.list_nodes()
            state = self._searchInObjectList(node, 'id', instanceId).state

    def _waitImageCreationCompleted(self, imageId):
        timeWait = 600
        timeStop = time.time() + timeWait

        imgState = None
        while imgState == None:
            if time.time() > timeStop:
                raise Exceptions.ExecutionException('Timed out while waiting for image "%s" to be created' % imageId)
            time.sleep(1)
            images = self._thread_local.driver.list_images()
            imgState = self._searchInObjectList(images, 'id', imageId)

    def _importKeypair(self, user_info):
        kp_name = 'ss-key-%i'  % int(time.time())
        public_key = self._getPublicSshKey(user_info)
        try:
            kp = self._thread_local.driver.ex_import_keypair_from_string(kp_name, public_key)
        except Exception as e:
            raise Exceptions.ExecutionException('Cannot import the public key. Reason: %s' % e)
        kp_name = kp.name
        self._userInfoSetKeypairName(user_info, kp_name)
        return kp_name

    def _createKeypairAndSetOnUserInfo(self, user_info):
        kp_name = 'ss-build-image-%i' % int(time.time())
        kp = self._thread_local.driver.ex_create_keypair(kp_name)
        self._userInfoSetPrivateKey(user_info, kp.private_key)
        self._userInfoSetKeypairName(user_info, kp.name)
        return kp.name

    def _deleteKeypair(self, kp_name):
        kp = self._searchInObjectList(self._thread_local.driver.ex_list_keypairs(), 'name', kp_name)
        self._thread_local.driver.ex_delete_keypair(kp)

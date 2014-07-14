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

from slipstream.NodeDecorator import KEY_RUN_CATEGORY
import slipstream.exceptions.Exceptions as Exceptions

from slipstream.cloudconnectors.cloudstack.CloudStackClientCloud import CloudStackClientCloud

import libcloud.security


def getConnector(configHolder):
    return getConnectorClass()(configHolder)


def getConnectorClass():
    return CloudStackAdvancedZoneClientCloud


class CloudStackAdvancedZoneClientCloud(CloudStackClientCloud):

    cloudName = 'cloudstack'

    def __init__(self, configHolder):
        libcloud.security.VERIFY_SSL_CERT = False

        super(CloudStackAdvancedZoneClientCloud, self).__init__(configHolder)
        self.run_category = getattr(configHolder, KEY_RUN_CATEGORY, None)

        self._capabilities = [] # Remove this workaround
        self.setCapabilities(contextualization=False,
                             generate_password=True,
                             direct_ip_assignment=True,
                             orchestrator_can_kill_itself_or_its_vapp=True)

    def initialization(self, user_info):
        super(CloudStackAdvancedZoneClientCloud, self).initialization(user_info)
        self.networks = self._thread_local.driver.ex_list_networks()

    def _startImageOnCloudStack(self, user_info, image_info, instance_name,
                                cloudSpecificData=None):
        imageId = self.getImageId(image_info)
        instance_name = self.formatInstanceName(instance_name)
        instanceType = self._getInstanceType(image_info)
        ipType = self.getCloudParameters(image_info)['network']

        keypair = None
        contextualizationScript = None
        if not self.isWindows():
            keypair = self._userInfoGetKeypairName(user_info)
            contextualizationScript = cloudSpecificData or None

        securityGroups = None
        security_groups = self._getCloudParameter(image_info, 'security.groups')
        if security_groups:
            securityGroups = [x.strip() for x in security_groups.split(',') if x]
        
        _networks = self._getCloudParameter(image_info, 'networks').split(',')
        try: 
            networks = [[i for i in self.networks if i.name == x.strip()][0] for x in _networks if x]
        except IndexError:
            raise Exceptions.ParameterNotFoundException(
                "Couldn't find one or more of the specified networks: %s" % _networks)
            
        try:
            size = [i for i in self.sizes if i.name == instanceType][0]
        except IndexError:
            raise Exceptions.ParameterNotFoundException(
                "Couldn't find the specified instance type: %s" % instanceType)
        try:
            image = [i for i in self.images if i.id == imageId][0]
        except IndexError:
            raise Exceptions.ParameterNotFoundException(
                "Couldn't find the specified image: %s" % imageId)

        if self.isWindows():
            instance = self._thread_local.driver.create_node(
                name=instance_name,
                size=size,
                image=image,
                ex_security_groups=securityGroups,
                networks=networks)
        else:
            instance = self._thread_local.driver.create_node(
                name=instance_name,
                size=size,
                image=image,
                ex_keyname=keypair,
                ex_security_groups=securityGroups,
                networks=networks)

        ip = self._get_instance_ip_address(instance, ipType)
        if not ip:
            raise Exceptions.ExecutionException("Couldn't find a '%s' IP" % ipType)

        vm = dict(networkType=ipType,
                  instance=instance,
                  ip=ip,
                  id=instance.id)
        return vm                

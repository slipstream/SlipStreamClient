import re
import time

from urlparse import urlparse

from slipstream.cloudconnectors.BaseCloudConnector import BaseCloudConnector
from slipstream.NodeDecorator import RUN_CATEGORY_IMAGE, RUN_CATEGORY_DEPLOYMENT, KEY_RUN_CATEGORY
from slipstream.utils.tasksrunner import TasksRunner
import slipstream.util as util
import slipstream.exceptions.Exceptions as Exceptions

from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver

from slipstream.cloudconnectors.cloudstack.libcloudPatch import patchLibcloud

import libcloud.security

def getConnector(configHolder):
    return getConnectorClass()(configHolder)

def getConnectorClass():
    return CloudStackClientCloud

class CloudStackClientCloud(BaseCloudConnector):

    cloudName = 'cloudstack'

    def __init__(self, configHolder):                
        libcloud.security.VERIFY_SSL_CERT = False
        patchLibcloud()
        
        super(CloudStackClientCloud, self).__init__(configHolder)
        self.run_category = getattr(configHolder, KEY_RUN_CATEGORY, None)
        
        self.setCapabilities(contextualization=True, 
                             direct_ip_assignment=True,
                             orchestrator_can_kill_itself_or_its_vapp=True)   

    def initialization(self, user_info):
        util.printStep('Initialize the CloudStack connector.')
        self._thread_local.driver = self._getDriver(user_info)
        self.sizes = self._thread_local.driver.list_sizes()
        self.images = self._thread_local.driver.list_images()
        self.user_info = user_info
        
        if self.run_category == RUN_CATEGORY_DEPLOYMENT:
            self._importKeypair(user_info)
        elif self.run_category == RUN_CATEGORY_IMAGE:
            #self._createKeypairAndSetOnUserInfo(user_info)
            raise NotImplementedError('The run category "%s" is not yet implemented')

    def finalization(self, user_info):
        try:
            kp_name = self._userInfoGetKeypairName(user_info)
            self._deleteKeypair(kp_name)
        except:
            pass

    def _startImage(self, user_info, image_info, instance_name, cloudSpecificData=None):
        self._thread_local.driver = self._getDriver(user_info)        
        return self._startImageOnCloudStack(user_info, image_info, instance_name, cloudSpecificData)
    
    def _startImageOnCloudStack(self, user_info, image_info, instance_name, cloudSpecificData=None):
        imageId = self.getImageId(image_info)
        instance_name = self.formatInstanceName(instance_name)
        instanceType = self._getInstanceType(image_info)
        ipType = self.getCloudParameters(image_info)['network']
        keypair = self._userInfoGetKeypairName(user_info)
        securityGroups = [x.strip() for x in self._getCloudParameter(image_info, 'security.groups').split(',') if x]
        try:
            size = [i for i in self.sizes if i.name == instanceType][0]
        except IndexError:
            raise Exceptions.ParameterNotFoundException("Couldn't find the specified instance type: %s" % instanceType)
        try:
            image = [i for i in self.images if i.id == imageId][0]
        except IndexError:
            raise Exceptions.ParameterNotFoundException("Couldn't find the specified image: %s" % imageId)
        contextualizationScript = cloudSpecificData or None
        
        if size == None: raise Exceptions.ParameterNotFoundException("Couldn't find the specified flavor: %s" % instanceType)
        if image == None: raise Exceptions.ParameterNotFoundException("Couldn't find the specified image: %s" % imageId)
        
        instance = self._thread_local.driver.create_node(name = instance_name,
                                           size = size, 
                                           image = image, 
                                           ex_keyname = keypair, 
                                           ex_userdata = contextualizationScript,
                                           ex_security_groups = securityGroups)
        
        ip = self._getInstanceIpAddress(instance, ipType)
        if not ip:
            raise Exceptions.ExecutionException("Couldn't find a '%s' IP" % ipType)
        
        vm = dict(networkType = ipType,
                  instance=instance, 
                  ip=ip, 
                  id=instance.id)
        return vm
    
    def _getCloudSpecificData(self, node_info, node_number, nodename):
        return self._getBootstrapScript(nodename)

    def listInstances(self):
        return self._thread_local.driver.list_nodes()   

    def _stopInstances(self, instances):
        tasksRunnner = TasksRunner()
        
        for instance in instances:
            driver = self._getDriver(self.user_info)
            tasksRunnner.run_task(driver.destroy_node, (instance,))
        tasksRunnner.wait_tasks_finished()

    def stopDeployment(self):
        instances = [vm['instance'] for vm in self.getVms().itervalues()]
        self._stopInstances(instances)
    
    def stopVmsByIds(self, ids):
        instances = [i for i in self.listInstances() if i.id in ids]
        self._stopInstances(instances)
    
    def _getDriver(self, userInfo):
        CloudStack = get_driver(Provider.CLOUDSTACK)
        
        url = urlparse(userInfo.get_cloud('endpoint'))
        secure = (url.scheme == 'https')
        
        return CloudStack(userInfo.get_cloud('username'), 
                          userInfo.get_cloud('password'), 
                          secure=secure,
                          host=url.hostname,
                          port=url.port,
                          path=url.path
                          );

    def vmGetIp(self, vm):
        return vm['ip']

    def vmGetId(self, vm):
        return vm['id']
    
    def _getInstanceIpAddress(self, instance, ipType):
        if ipType.lower() == 'private': 
            return (len(instance.private_ip) != 0) and instance.private_ip[0] or ''
        else:
            return (len(instance.public_ip) != 0) and instance.public_ip[0] or ''
            
    def _importKeypair(self, user_info):
        kp_name = 'ss-key-%i'  % int(time.time())
        public_key = self._getPublicSshKey(user_info)
        try:
            kp = self._thread_local.driver.ex_import_keypair_from_string(kp_name, public_key)
        except Exception as e:
            raise Exceptions.ExecutionException('Cannot import the public key. Reason: %s' % e)
        kp_name = kp.get('keyName', None)
        self._userInfoSetKeypairName(user_info, kp_name)
        return kp_name
            
    def _createKeypairAndSetOnUserInfo(self, user_info):
        kp_name = 'ss-build-image-%i' % int(time.time())
        kp = self._thread_local.driver.ex_create_keypair(kp_name)
        self._userInfoSetPrivateKey(user_info, kp.private_key)
        self._userInfoSetKeypairName(user_info, kp.name)
        return kp.get('keyName', None)

    def _deleteKeypair(self, kp_name):
        return self._thread_local.driver.ex_delete_keypair(kp_name)

    def formatInstanceName(self, name):
        name = self.removeBadCharInInstanceName(name)
        return self.truncateInstanceName(name)

    def truncateInstanceName(self, name):
        if len(name) <= 63:
            return name
        else:
            return name[:31] + '-' + name[-31:]

    def removeBadCharInInstanceName(self, name):
        try:
            newname = re.sub(r'[^a-zA-Z0-9-]','', name)
            m = re.search('[a-zA-Z]([a-zA-Z0-9-]*[a-zA-Z0-9]+)?', newname)
            return m.string[m.start():m.end()]
        except:
            raise Exceptions.ExecutionException('Cannot handle the instance name "%s". Instance name can contain ASCII letters "a" through "z", the digits "0" through "9", and the hyphen ("-"), must be between 1 and 63 characters long, and can\'t start or end with "-" and can\'t start with digit' % name)
        
    


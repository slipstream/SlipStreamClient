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

from slipstream.cloudconnectors.BaseCloudConnector import BaseCloudConnector
import slipstream.util as util


def getConnector(configHolder):
    return getConnectorClass()(configHolder)


def getConnectorClass():
    return PhysicalHostClientCloud


class PhysicalHostClientCloud(BaseCloudConnector):
    cloudName = 'physicalhost'

    def __init__(self, configHolder):
        super(PhysicalHostClientCloud, self).__init__(configHolder)

        self.setCapabilities(contextualization=True,
                             direct_ip_assignment=True,
                             orchestrator_can_kill_itself_or_its_vapp=True)

    def initialization(self, user_info):
    #        for node_info in nodes_info:
    #            if node_info['multiplicity'] > 1:
    #                raise Exceptions.ExecutionException('Multiplicity not yet supported by this connector.')

        # TODO: username, password and privateKey should be taken from Image Info
        self.username = user_info.get_cloud('username')
        self.password = user_info.get_cloud('password')
        self.privateKey = self._getSshPrivateKey(user_info)
        image_info = {'attributes': {'loginUser': self.username},
                      'cloud_parameters': {self.cloudName:
                                           {self.cloudName+'.login.password': self.password}}
                      }
        self.addVm('orchestrator-physicalhost', {'username': self.username,
                                                 'password': self.password,
                                                 'privateKey': self.privateKey,
                                                 'host': os.environ['PHYSICALHOST_ORCHESTRATOR_HOST'],
                                                 'id': os.environ['PHYSICALHOST_ORCHESTRATOR_HOST'],
                                                 'ip': os.environ['PHYSICALHOST_ORCHESTRATOR_HOST']},
                                                 image_info)

    def _startImage(self, user_info, image_info, instance_name, cloudSpecificData=None):
        host = self.getImageId(image_info)
        command = cloudSpecificData

        self._runScriptWithPrivateKey(host, self.username, command, self.password, self.privateKey)

        vm = {'username': self.username,
              'privateKey': self.privateKey,
              'password': self.password,
              'host': host,
              'id': host,
              'ip': host}
        return vm

    def vmGetIp(self, host):
        return host['ip']

    def vmGetId(self, host):
        return host['id']

    def stopDeployment(self):
        for nodename, node in self.getVms().items():
            if not nodename == 'orchestrator-physicalhost':
                self._stopImages(node['username'], node['privateKey'], node['password'], node['host'])

    def stopVmsByIds(self, ids):
        util.printAndFlush("Stop ids: %s" % ids)
        for _, node in self.getVms().items():
            util.printAndFlush("   Node: %s" % node['host'])
            if node['host'] in ids:
                self._stopImages(node['username'], node['privateKey'], node['password'], node['host'])

    def _getCloudSpecificData(self, node_info, node_number, nodename):
        return self._buildContextualizationScript(nodename, self.username)

    def _buildContextualizationScript(self, nodename, username):
        sudo = self._getSudo(username)

        userData = "echo '(" + sudo + " bash -c '\\''sleep 5; "
        for (k, v) in os.environ.items():
            if k.startswith('SLIPSTREAM_') or k.startswith('PHYSICALHOST_'):
                userData += 'export ' + k + '="' + v + '"' + "; "
        userData += 'export SLIPSTREAM_NODENAME="' + nodename + '"' + "; "
        userData += self.__build_slipstream_bootstrap_command(nodename)
        userData += "'\\'') > /dev/null 2>&1 &' | at now"
        return userData

    def _stopImages(self, username, privateKey, password, host):
        sudo = self._getSudo(username)

        command = sudo + " bash -c '"
        #command = "echo '(sudo bash -c '\\''"
        #command += 'kill -9 `ps -Af | grep python | grep slipstream | grep -v grep | awk "{print $2}"`; ';
        command += "rm -R /tmp/slipstream*; rm /tmp/tmp*; rm -R /opt/slipstream; rm -R /opt/paramiko; "
        command += "'"
        #command += "'\\'') > /dev/null 2>&1 &' | at now"

        self._runScriptWithPrivateKey(host, username, command, password, privateKey)

    def _getSudo(self, username):
        if username == 'root':
            return ''
        else:
            return 'sudo'

    def _runScriptWithPrivateKey(self, host, username, command, password, privateKey):
        sshPrivateKeyFile = None
        if privateKey:
            sshPrivateKeyFile = util.file_put_content_in_temp_file(privateKey)
        try:
            self._run_script(host, username, command, password, sshPrivateKeyFile)
        finally:
            try:
                os.unlink(sshPrivateKeyFile)
            except:
                pass

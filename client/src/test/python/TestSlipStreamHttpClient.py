#!/usr/bin/env python
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

import os
import unittest
from mock import Mock

from slipstream.SlipStreamHttpClient import SlipStreamHttpClient
from slipstream.SlipStreamHttpClient import DomExtractor
from slipstream.ConfigHolder import ConfigHolder
from slipstream import util
from slipstream.NodeDecorator import NodeDecorator

etree = util.importETree()

'''This test suite tests SlipStreamHttpClient against Run and User XML
renderings.
'''


def _get_resources_path():
    level_up = os.path.split(os.path.dirname(__file__))[0]
    return os.path.join(level_up, 'resources')


with open(os.path.join(_get_resources_path(), 'run.xml')) as fd:
    RUN_XML = fd.read()
RUN_ETREE = etree.fromstring(RUN_XML)

with open(os.path.join(_get_resources_path(), 'configuration.xml')) as fd:
    CONFIGURATION_XML = fd.read()
CONFIGURATION_ETREE = etree.fromstring(CONFIGURATION_XML)

NODES_NUM = 2
NODE_INSTANCES_NUM = 2
CLOUD_NAME = 'myCloud'


class SlipStreamHttpClientTestCase(unittest.TestCase):

    def setUp(self):
        self.context = {}
        self.context['diid'] = '1234'
        self.context['serviceurl'] = 'endpoint'
        self.context['username'] = 'username'
        self.context['password'] = 'password'
        self.context[NodeDecorator.NODE_INSTANCE_NAME_KEY] = 'apache'

    def tearDown(self):
        pass

    def test_get_run_category(self):

        configHolder = ConfigHolder(config={'foo': 'bar'}, context=self.context)
        client = SlipStreamHttpClient(configHolder)
        client._httpGet = Mock(return_value=(200, '<run category="foo" />'))

        self.assertEquals('foo', client.get_run_category())
        self.assertEquals('foo', client.get_run_category())

        self.assertEquals(1, client._httpGet.call_count)

    def test_get_deployment_targets(self):
        targets = DomExtractor.extract_node_image_targets(RUN_ETREE, 'apache')
        self.assertEquals(True,
                          targets['execute'][-1].get('script', '').startswith('#!/bin/sh -xe\napt-get update -y\n'))

        targets = DomExtractor.extract_node_image_targets(RUN_ETREE, 'testclient')
        self.assertEquals(targets['execute'][-1].get('script', '').startswith(
            '#!/bin/sh -xe\n# Wait for the metadata to be resolved\n'),
            True)

    def test_extract_node_instances_from_run(self):
        nodes = DomExtractor.extract_nodes_instances_runtime_parameters(
            RUN_ETREE, CLOUD_NAME)
        self.assertEquals(NODE_INSTANCES_NUM, len(nodes) - 1)
        for node_instance_name, node_instance in nodes.iteritems():
            assert node_instance_name == node_instance[NodeDecorator.NODE_INSTANCE_NAME_KEY]
            assert isinstance(node_instance, dict)
            self.assertEquals('myCloud', node_instance['cloudservice'])

    def test_extract_nodes_runtime_parameters(self):
        nodes = DomExtractor.extract_nodes_runtime_parameters(RUN_ETREE)
        self.assertEquals(NODES_NUM, len(nodes))

    def test_get_build_targets_from_image_module(self):
        package1 = 'vim-enhanced'
        package2 = 'yum-utils'
        prerecipe = 'echo prerecipe'
        recipe = 'echo recipe'

        image_module_xml = """
<imageModule category="Image">
   <targets class="org.hibernate.collection.PersistentBag"/>
   <targetsExpanded class="java.util.HashSet">
      <targetExpanded name="prerecipe">
         <subTarget name="prerecipe" order="1"><![CDATA[%(prerecipe)s]]></subTarget>
      </targetExpanded>
      <targetExpanded name="recipe">
         <subTarget name="recipe" order="1"><![CDATA[%(recipe)s]]></subTarget>
      </targetExpanded>
   </targetsExpanded>
   <packagesExpanded class="org.hibernate.collection.PersistentBag">
      <packageExpanded name="%(package1)s"/>
      <packageExpanded name="%(package2)s"/>
   </packagesExpanded>
   <prerecipe><![CDATA[%(prerecipe)s]]></prerecipe>
   <recipe><![CDATA[%(recipe)s]]></recipe>
</imageModule>
""" % {'package1': package1,
       'package2': package2,
       NodeDecorator.NODE_PRERECIPE: prerecipe,
       NodeDecorator.NODE_RECIPE: recipe}

        dom = etree.fromstring(image_module_xml)
        targets = DomExtractor.get_targets_from_module(dom)

        failMsg = "Failure getting '%s' build target."
        assert targets.get(NodeDecorator.NODE_PRERECIPE)[-1].get(
            'script') == prerecipe, failMsg % NodeDecorator.NODE_PRERECIPE
        assert targets.get(NodeDecorator.NODE_RECIPE)[-1].get('script') == recipe, failMsg % NodeDecorator.NODE_RECIPE
        assert isinstance(targets[NodeDecorator.NODE_PACKAGES], list), failMsg % NodeDecorator.NODE_PACKAGES
        assert package1 in targets[NodeDecorator.NODE_PACKAGES], failMsg % NodeDecorator.NODE_PACKAGES
        assert package2 in targets[NodeDecorator.NODE_PACKAGES], failMsg % NodeDecorator.NODE_PACKAGES

    def test_get_extra_disks(self):
        nodes = RUN_ETREE.findall(DomExtractor.PATH_TO_NODE_ON_RUN)
        for node in nodes:
            image = node.find('image')
            extra_disks = DomExtractor.get_extra_disks_from_image(image)
            if node.get('name') == 'testclient':
                assert {} == extra_disks
            elif node.get('name') == 'apache':
                assert '1' == extra_disks[DomExtractor.EXTRADISK_VOLATILE_KEY]

    def test_cloud_params_and_network(self):
        client = SlipStreamHttpClient(ConfigHolder(context=self.context,
                                                   config={'foo': 'bar'}))
        client._httpGet = Mock(return_value=(200, RUN_XML))

        nodes = client.get_nodes_instances()
        node = nodes['apache.1']

        assert node.get_cpu() is None
        assert node.get_instance_type() == 'm1.small'
        assert node.get_security_groups() == []
        assert node.get_network_type() == 'Public'

    def test_get_nodes_instances(self):
        client = SlipStreamHttpClient(ConfigHolder(context=self.context,
                                                   config={'foo': 'bar'}))
        client._httpGet = Mock(return_value=(200, RUN_XML))

        nodes_instances = client.get_nodes_instances()
        assert len(nodes_instances) == NODE_INSTANCES_NUM + 1

        node_keys = ['cloudservice', NodeDecorator.NODE_NAME_KEY,
                     NodeDecorator.NODE_INSTANCE_NAME_KEY, 'id']
        for nodes_instance in nodes_instances:
            for key in node_keys:
                if nodes_instances[nodes_instance].is_orchestrator() == 'false':
                    self.assertTrue(key in nodes_instances[nodes_instance],
                                    'No element %s' % key)

    user_email = 'test@sixsq.com'
    user_param_sshkey = 'ssh-rsa abc'
    user_param_timeout = 60
    cloud_endpoint = 'https://api.exoscale.ch/compute'
    connector_zone = 'CH-GVA-2'
    cloud_name = 'exoscale-ch-gva'
    cloud_key = 'foo'
    cloud_secret = 'bar'

    resource_user = {
        "activeSince": "2018-01-15T10:39:56.655Z",
        "lastExecute": "2018-01-18T09:03:40.454Z",
        "deleted": False,
        "password": "xxx",
        "method": "auto",
        "updated": "2018-02-17T23:19:27.449Z",
        "emailAddress": user_email,
        "roles": "",
        "username": "konstan",
        "firstName": "Konstantin",
        "created": "2013-12-18T16:21:23.823Z",
        "state": "ACTIVE",
        "organization": "SixSq",
        "lastOnline": "2018-01-12T09:04:09.445Z",
        "id": "user/konstan",
        "lastName": "Skaburskas",
        "acl": {
            "owner": {
                "principal": "ADMIN",
                "type": "ROLE"
            },
            "rules": [
                {
                    "principal": "ADMIN",
                    "right": "ALL",
                    "type": "ROLE"
                },
                {
                    "principal": "konstan",
                    "right": "MODIFY",
                    "type": "USER"
                }
            ]
        },
        "operations": [
            {
                "rel": "edit",
                "href": "user/konstan"
            },
            {
                "rel": "delete",
                "href": "user/konstan"
            }
        ],
        "resourceURI": "http://sixsq.com/slipstream/1/User",
        "isSuperUser": False,
        "githublogin": "konstan"
    }
    resource_user_param = {
        "count": 1,
        "acl": {
            "owner": {
                "principal": "ADMIN",
                "type": "ROLE"
            },
            "rules": [{
                "principal": "USER",
                "type": "ROLE",
                "right": "MODIFY"
            }]
        },
        "resourceURI": "http://sixsq.com/slipstream/1/UserParamsCollection",
        "id": "user-param",
        "operations": [{
            "rel": "add",
            "href": "user-param"
        }],
        "userParam": [{
            "updated": "2018-02-17T23:19:23.876Z",
            "created": "2018-01-15T10:39:56.793Z",
            "defaultCloudService": cloud_name,
            "id": "user-param/f8bcc895-bc06-46be-971b-fa39de97ab0d",
            "acl": {
                "owner": {
                    "principal": "konstan",
                    "type": "USER"
                },
                "rules": [{
                    "principal": "ADMIN",
                    "right": "ALL",
                    "type": "ROLE"
                }, {
                    "principal": "konstan",
                    "right": "MODIFY",
                    "type": "USER"
                }]
            },
            "operations": [{
                "rel": "edit",
                "href": "user-param/f8bcc895-bc06-46be-971b-fa39de97ab0d"
            }, {
                "rel": "delete",
                "href": "user-param/f8bcc895-bc06-46be-971b-fa39de97ab0d"
            }],
            "resourceURI": "http://sixsq.com/slipstream/1/UserParam",
            "timeout": user_param_timeout,
            "sshPublicKey": user_param_sshkey,
            "verbosityLevel": 3,
            "keepRunning": "never",
            "mailUsage": "daily",
            "paramsType": "execution"
        }]
    }
    resource_cloud_cred = {
        "count": 1,
        "acl": {
            "owner": {
                "principal": "ADMIN",
                "type": "ROLE"
            },
            "rules": [{
                "principal": "ADMIN",
                "type": "ROLE",
                "right": "MODIFY"
            }, {
                "principal": "USER",
                "type": "ROLE",
                "right": "MODIFY"
            }]
        },
        "resourceURI": "http://sixsq.com/slipstream/1/CredentialCollection",
        "id": "credential",
        "operations": [{
            "rel": "add",
            "href": "credential"
        }],
        "credentials": [{
            "connector": {
                "href": "connector/%s" % cloud_name
            },
            "key": cloud_key,
            "method": "store-cloud-cred-exoscale",
            "updated": "2018-02-17T23:19:25.534Z",
            "name": cloud_name,
            "type": "cloud-cred-exoscale",
            "created": "2017-12-19T10:07:00.713Z",
            "secret": cloud_secret,
            "quota": 50,
            "domain-name": "",
            "id": "credential/2a545b22-1f8c-4094-8c2f-28c96f3fea21",
            "acl": {
                "owner": {
                    "principal": "konstan",
                    "type": "USER"
                },
                "rules": [{
                    "principal": "ADMIN",
                    "right": "ALL",
                    "type": "ROLE"
                }, {
                    "principal": "konstan",
                    "right": "MODIFY",
                    "type": "USER"
                }]
            },
            "operations": [{
                "rel": "edit",
                "href": "credential/2a545b22-1f8c-4094-8c2f-28c96f3fea21"
            }, {
                "rel": "delete",
                "href": "credential/2a545b22-1f8c-4094-8c2f-28c96f3fea21"
            }],
            "resourceURI": "http://sixsq.com/slipstream/1/Credential"
        }]
    }
    resource_connector = {
        "securityGroups": "slipstream_managed",
        "cloudServiceType": "exoscale",
        "orchestratorInstanceType": "Micro",
        "instanceName": cloud_name,
        "zone": connector_zone,
        "updated": "2018-02-18T21:25:39.402Z",
        "updateClientURL": "https://185.19.28.68/downloads/exoscaleclient.tgz",
        "created": "2016-10-25T07:22:05.339Z",
        "quotaVm": "",
        "nativeContextualization": "linux-only",
        "id": "connector/%s" % cloud_name,
        "acl": {
            "owner": {
                "principal": "ADMIN",
                "type": "ROLE"
            },
            "rules": [{
                "principal": "USER",
                "right": "VIEW",
                "type": "ROLE"
            }, {
                "principal": "ADMIN",
                "right": "ALL",
                "type": "ROLE"
            }, {
                "principal": "ADMIN",
                "right": "VIEW",
                "type": "ROLE"
            }]
        },
        "resourceURI": "http://sixsq.com/slipstream/1/Connector",
        "orchestratorSSHUsername": "",
        "maxIaasWorkers": 20,
        "orchestratorDisk": "10G",
        "orchestratorImageid": "Linux Ubuntu 14.04 LTS 64-bit",
        "endpoint": cloud_endpoint,
        "orchestratorSSHPassword": ""
    }

    def get_user_info(self):
        ch = ConfigHolder(config={'foo': 'bar'}, context={})
        ch.context = {}
        client = SlipStreamHttpClient(ch)
        client._get_user = Mock(return_value=client._strip_unwanted_attrs(self.resource_user))
        client._get_user_params = Mock(return_value=client._strip_unwanted_attrs(
            self.resource_user_param.get('userParam')[0]))
        client._get_cloud_creds = Mock(return_value=client._strip_unwanted_attrs(self.resource_cloud_cred))
        client._get_connector_conf = Mock(return_value=client._strip_unwanted_attrs(self.resource_connector))

        return client.get_user_info(self.cloud_name)

    def test_getUserInfo(self):
        user_info = self.get_user_info()
        assert user_info.get_general('password') is None
        assert self.user_email == user_info.get_user('emailAddress')
        assert self.cloud_endpoint == user_info.get_cloud('endpoint')
        assert self.connector_zone == user_info.get_cloud('zone')
        assert self.user_param_sshkey == user_info.get_public_keys()
        assert self.user_param_timeout == user_info.get_general('timeout')
        assert self.cloud_key == user_info.get_cloud('key')
        assert self.cloud_key == user_info.get_cloud('username')
        assert self.cloud_secret == user_info.get_cloud('secret')
        assert self.cloud_secret == user_info.get_cloud('password')

    def test_getUserInfo_empty_param(self):
        user_info = self.get_user_info()

        param = 'orchestratorSSHPassword'

        # Check when the value of the parameter is emply.
        assert '' == user_info.get_cloud(param)
        assert '' == user_info.get_cloud(param, 'default')

        # Re-set value to None.
        user_info['%s.%s' % (self.cloud_name, param)] = None
        assert None is user_info.get_cloud(param)
        assert None is user_info.get_cloud(param, 'default')

    def test_getUserInfo_nonexistent_param(self):
        user_info = self.get_user_info()
        param = 'doesnotexist'
        assert None is user_info.get_cloud(param)
        assert 'default' == user_info.get_cloud(param, 'default')

    def test_server_config_dom_into_dict(self):
        conf = DomExtractor.server_config_dom_into_dict(CONFIGURATION_ETREE)
        assert conf
        assert isinstance(conf, dict)

    def test_server_config_dom_into_dict_value_updater(self):
        base_url_param = 'slipstream.base.url'
        base_url_value_orig = ''
        base_url_value_new = 'UPDATED'
        conf = DomExtractor.server_config_dom_into_dict(CONFIGURATION_ETREE)
        for k, v in conf['SlipStream_Basics']:
            if k == base_url_param:
                base_url_value_orig = v

        def _updater(value):
            return value == base_url_value_orig and base_url_value_new or value

        conf = DomExtractor.server_config_dom_into_dict(CONFIGURATION_ETREE,
                                                        value_updater=_updater)
        for k, v in conf['SlipStream_Basics']:
            if k == base_url_param:
                assert v == base_url_value_new


if __name__ == '__main__':
    unittest.main()

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

with open(os.path.join(_get_resources_path(), 'user.xml')) as fd:
    USER_XML = fd.read()

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
        self.assertEquals(True, targets['execute'][-1].get('script','').startswith('#!/bin/sh -xe\napt-get update -y\n'))

        targets = DomExtractor.extract_node_image_targets(RUN_ETREE, 'testclient')
        self.assertEquals(targets['execute'][-1].get('script','').startswith('#!/bin/sh -xe\n# Wait for the metadata to be resolved\n'),
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
        assert targets.get(NodeDecorator.NODE_PRERECIPE)[-1].get('script') == prerecipe, failMsg % NodeDecorator.NODE_PRERECIPE
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

    def test_getUserInfoUser(self):
        client = SlipStreamHttpClient(ConfigHolder(config={'foo': 'bar'},
                                                   context=self.context))
        client._getUserContent = Mock(return_value=USER_XML)
        userInfo = client.get_user_info('')
        assert 'Test' == userInfo.get_user('firstName')
        assert 'User' == userInfo.get_user('lastName')
        assert 'test@sixsq.com' == userInfo.get_user('email')
        assert '30' == userInfo.get_general('Timeout')

    def test_getUserInfo(self):
        client = SlipStreamHttpClient(ConfigHolder(config={'foo': 'bar'},
                                                   context=self.context))
        client._getUserContent = Mock(return_value=USER_XML)
        userInfo = client.get_user_info('StratusLab')

        assert 'test@sixsq.com' == userInfo.get_user('email')

        assert 'cloud.lal.stratuslab.eu' == userInfo.get_cloud('endpoint')
        assert 'public' == userInfo.get_cloud('ip.type')
        assert 'ssh-rsa abc' == userInfo.get_general('ssh.public.key')

        assert 'on' == userInfo.get_general('On Error Run Forever')
        assert '3' == userInfo.get_general('Verbosity Level')

    def test_getUserInfo_empty_param(self):
        client = SlipStreamHttpClient(ConfigHolder(config={'foo': 'bar'},
                                                   context=self.context))
        client._getUserContent = Mock(return_value=USER_XML)
        userInfo = client.get_user_info('StratusLab')
        param = 'domain.name'
        assert '' == userInfo.get_cloud(param)
        assert '' == userInfo.get_cloud(param, 'default')

    def test_getUserInfo_nonexistent_param(self):
        client = SlipStreamHttpClient(ConfigHolder(config={'foo': 'bar'},
                                                   context=self.context))
        client._getUserContent = Mock(return_value=USER_XML)
        userInfo = client.get_user_info('StratusLab')
        param = 'doesnotexist'
        assert None == userInfo.get_cloud(param)
        assert 'default' == userInfo.get_cloud(param, 'default')

    def test_server_config_dom_into_dict(self):
        conf = DomExtractor.server_config_dom_into_dict(CONFIGURATION_ETREE)
        assert conf
        assert isinstance(conf, dict)

    def test_server_config_dom_into_dict_value_updater(self):
        base_url_param ='slipstream.base.url'
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

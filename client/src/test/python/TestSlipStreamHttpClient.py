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

from requests.cookies import RequestsCookieJar, create_cookie
import requests

from slipstream.exceptions.Exceptions import NetworkError

from slipstream.SlipStreamHttpClient import SlipStreamHttpClient, get_cookie
from slipstream.SlipStreamHttpClient import DomExtractor
from slipstream.ConfigHolder import ConfigHolder
from slipstream import util
from slipstream.NodeDecorator import NodeDecorator
from slipstream.api import Api

etree = util.importETree()

'''This test suite tests SlipStreamHttpClient against Run and User XML
renderings.
'''

Api.login_internal = Mock()
Api.login_apikey = Mock()


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

    def test_init_session_fail_no_creds(self):
        ch = ConfigHolder()
        ch.context = {}
        ch.set('verboseLevel', 0)
        ch.set('cookie_filename', '/dev/null')

        client = SlipStreamHttpClient(ch)
        client.init_session('http://foo.bar')
        assert client.session is not None
        assert client.session.login_params == {}
        resp = Mock(spec=requests.Response)
        resp.status_code = 403
        resp.headers = {}
        client.session._request = Mock(return_value=resp)
        client.session.cimi_login = Mock()
        try:
            client.get('http://foo.bar', retry=False)
        except Exception as ex:
            assert ex.code == 403
        assert client.session.cimi_login.called is True

    def test_init_session_login_internal(self):
        ch = ConfigHolder()
        ch.context = {}
        ch.set('verboseLevel', 0)
        ch.set('cookie_filename', '/dev/null')
        ch.set('username', 'foo')
        ch.set('password', 'bar')

        client = SlipStreamHttpClient(ch)
        client.init_session('http://foo.bar')
        assert client.session is not None
        assert client.session.login_params
        assert 'username' in client.session.login_params
        assert 'password' in client.session.login_params

    def test_init_session_login_apikey(self):
        ch = ConfigHolder()
        ch.context = {}
        ch.set('verboseLevel', 0)
        ch.set('cookie_filename', '/dev/null')
        ch.set('api_key', 'key')
        ch.set('api_secret', 'secret')

        client = SlipStreamHttpClient(ch)
        client.init_session('http://foo.bar')
        assert client.session is not None
        assert client.session.login_params
        assert 'key' in client.session.login_params
        assert 'secret' in client.session.login_params

    def test_unknown_http_return_code(self):
        ch = ConfigHolder()
        client = SlipStreamHttpClient(ch)
        client.verboseLevel = 0
        client.session = Mock()
        client.session.cookies = []
        resp = Mock(spec_set=requests.Response())
        resp.request = Mock()
        resp.request.headers = {}
        resp.status_code = 999
        client.session.request = Mock(return_value=resp)

        self.assertRaises(NetworkError, client.get, 'http://foo.bar',
                          retry=False)

    def test_post_with_data(self):
        ch = ConfigHolder()
        ch.context = {}
        ch.set('verboseLevel', 0)
        ch.set('cookie_filename', '/dev/null')
        ch.set('api_key', 'key')
        ch.set('api_secret', 'secret')
        client = SlipStreamHttpClient(ch)
        resp = requests.Response()
        resp.status_code = 200
        resp.get = Mock(return_value=None)
        resp.request = Mock()
        resp.request.headers = {}
        requests.sessions.Session.send = Mock(return_value=resp)

        client.post('http://example.com', 'a=b\nc=d')

        args, kwargs = requests.sessions.Session.send.call_args
        self.assertEqual(len(args), 1)
        req = args[0]
        self.assertEqual(req.body, 'a=b\nc=d')

    def test_get_cookie(self):
        self.assertIsNone(get_cookie(RequestsCookieJar(), None))

        cookie_str = 'cookie.name=this is a cookie'
        name, value = cookie_str.split('=')
        domain = 'example.com'
        path = '/some'

        jar = RequestsCookieJar()
        cookie = create_cookie(name, value, **{'domain': domain, 'path': path})
        jar.set_cookie(cookie)

        # w/o path
        self.assertIsNone(get_cookie(jar, None))
        self.assertIsNone(get_cookie(jar, domain))
        c_str = get_cookie(jar, domain, name=name)
        self.assertIsNotNone(c_str)
        self.assertEquals(cookie_str, c_str)

        # w/ path
        self.assertIsNone(get_cookie(jar, domain, path='/', name=name))

        c_str = get_cookie(jar, domain, path='/some', name=name)
        self.assertEquals(cookie_str, c_str)

        c_str = get_cookie(jar, domain, path='/some/path', name=name)
        self.assertEquals(cookie_str, c_str)

        # root path cookie
        jar = RequestsCookieJar()
        cookie = create_cookie(name, value, **{'domain': domain, 'path': '/'})
        jar.set_cookie(cookie)
        c_str = get_cookie(jar, domain, path='/', name=name)
        self.assertEquals(cookie_str, c_str)

        c_str = get_cookie(jar, domain, path='/random', name=name)
        self.assertEquals(cookie_str, c_str)

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
        userInfo = client.get_user_info('SomeCloud')

        assert 'test@sixsq.com' == userInfo.get_user('email')

        assert 'cloud.lal.somecloud.eu' == userInfo.get_cloud('endpoint')
        assert 'public' == userInfo.get_cloud('ip.type')
        assert 'ssh-rsa abc' == userInfo.get_general('ssh.public.key')

        assert 'on' == userInfo.get_general('On Error Run Forever')
        assert '3' == userInfo.get_general('Verbosity Level')

    def test_getUserInfo_empty_param(self):
        client = SlipStreamHttpClient(ConfigHolder(config={'foo': 'bar'},
                                                   context=self.context))
        client._getUserContent = Mock(return_value=USER_XML)
        user_info = client.get_user_info('SomeCloud')

        param = 'domain.name'

        # Check when the value of the parameter is emply.
        assert '' == user_info.get_cloud(param)
        assert '' == user_info.get_cloud(param, 'default')

        # Re-set value to None.
        user_info['SomeCloud.' + param] = None
        assert None == user_info.get_cloud(param)
        assert None == user_info.get_cloud(param, 'default')

    def test_getUserInfo_nonexistent_param(self):
        client = SlipStreamHttpClient(ConfigHolder(config={'foo': 'bar'},
                                                   context=self.context))
        client._getUserContent = Mock(return_value=USER_XML)
        user_info = client.get_user_info('SomeCloud')
        param = 'doesnotexist'
        assert None == user_info.get_cloud(param)
        assert 'default' == user_info.get_cloud(param, 'default')

    def test_getUserInfo_param_wthout_value_tag(self):
        client = SlipStreamHttpClient(ConfigHolder(config={'foo': 'bar'},
                                                   context=self.context))
        client._getUserContent = Mock(return_value=USER_XML)
        user_info = client.get_user_info('SomeCloud')

        param = 'no.value'

        assert '' == user_info.get_cloud(param)
        assert '' == user_info.get_cloud(param, 'default')

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

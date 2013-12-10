#!/usr/bin/env python
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

import unittest
from mock import Mock
from xml.etree import ElementTree

from slipstream.SlipStreamHttpClient import SlipStreamHttpClient
from slipstream.SlipStreamHttpClient import DomExtractor
from slipstream.ConfigHolder import ConfigHolder
from slipstream import util

etree = util.importETree()

RUN_XML = """<run category="Deployment" deleted="false" resourceUri="run/f5f75421-b151-4c1a-87e3-8b5e659fbee6" uuid="f5f75421-b151-4c1a-87e3-8b5e659fbee6" type="Orchestration" cloudServiceName="stratuslab" moduleResourceUri="module/Public/Tutorials/HelloWorld/client_server/11" startTime="2013-01-09 10:58:29.122 UTC" nodeNames="orchestrator-stratuslab, testclient1.1, apache1.1, " user="test" creation="2013-01-09 11:02:00.20 UTC" state="Inactive" status="Inactive" groups="stratuslab:testclient1, stratuslab:apache1, ">
<parameters class="org.hibernate.collection.PersistentMap">
   <entry>
      <string><![CDATA[apache1--cloudservice]]></string>
      <parameter class="com.sixsq.slipstream.persistence.RunParameter" name="apache1--cloudservice" description="Cloud Service where the node resides" category="General" mandatory="false" type="String" readonly="false">
         <value><![CDATA[default]]></value>
      </parameter>
   </entry>
   <entry>
      <string><![CDATA[testclient1--multiplicity]]></string>
      <parameter class="com.sixsq.slipstream.persistence.RunParameter" name="testclient1--multiplicity" description="Multiplicity number" category="General" mandatory="false" type="String" readonly="false">
         <value><![CDATA[1]]></value>
      </parameter>
   </entry>
   <entry>
      <string><![CDATA[testclient1--cloudservice]]></string>
      <parameter class="com.sixsq.slipstream.persistence.RunParameter" name="testclient1--cloudservice" description="Cloud Service where the node resides" category="General" mandatory="false" type="String" readonly="false">
         <value><![CDATA[default]]></value>
      </parameter>
   </entry>
   <entry>
      <string><![CDATA[apache1--multiplicity]]></string>
      <parameter class="com.sixsq.slipstream.persistence.RunParameter" name="apache1--multiplicity" description="Multiplicity number" category="General" mandatory="false" type="String" readonly="false">
         <value><![CDATA[1]]></value>
      </parameter>
   </entry>
</parameters>
<runtimeParameters class="org.hibernate.collection.PersistentMap">
   <entry>
      <string><![CDATA[apache1.1:extra_disk_volatile]]></string>
      <runtimeParameter deleted="false" key="apache1.1:extra_disk_volatile" isSet="false" group="apache1.1" mapsOthers="false" mappedRuntimeParameterNames="" isMappedValue="false" creation="2013-01-09 11:02:00.22 UTC"><![CDATA[]]></runtimeParameter>
   </entry>
</runtimeParameters>
<module lastModified="2012-12-17 10:31:02.987 CET" category="Deployment" deleted="false" resourceUri="module/test/dpl/14" parentUri="module/test" name="test/dpl" version="14" creation="2012-12-17 10:31:02.948 CET" shortName="dpl">
   <parameters class="org.hibernate.collection.PersistentMap"/>
   <nodes class="org.hibernate.collection.PersistentMap">
      <entry>
         <string>ubuntu1</string>
         <node deleted="false" name="ubuntu1" multiplicity="1" cloudService="foo" imageUri="module/test/ubuntu1" creation="2012-12-17 22:54:34.977 CET">
            <parameters class="org.hibernate.collection.PersistentMap"/>
            <parameterMappings class="org.hibernate.collection.PersistentMap"/>
            <image lastModified="2012-12-17 10:30:11.259 CET" category="Image" deleted="false" resourceUri="module/test/ubuntu1/13" parentUri="module/test" name="test/ubuntu1" version="13" isBase="true" imageId="d02ee717-33f7-478b-ba14-0219
6978fea8" creation="2012-12-17 10:30:11.244 CET" shortName="ubuntu1" instanceType="inherited" loginUser="ubuntu" platform="ubuntu">
               <parameters class="org.hibernate.collection.PersistentMap">
                  <entry>
                      <string><![CDATA[extra.disk.volatile]]></string>
                      <parameter class="com.sixsq.slipstream.persistence.ModuleParameter" name="extra.disk.volatile" description="Volatile extra disk in GB" category="Cloud" mandatory="true" type="String" readonly="false"/>
                   </entry>
                   <entry>
                     <string><![CDATA[cloudsigma.ram]]></string>
                     <parameter class="com.sixsq.slipstream.persistence.ModuleParameter" name="cloudsigma.ram" description="RAM in GB" category="cloudsigma" mandatory="true" type="String" readonly="false">
                        <value><![CDATA[1]]></value>
                     </parameter>
                  </entry>
                  <entry>
                     <string><![CDATA[hostname]]></string>
                     <parameter class="com.sixsq.slipstream.persistence.ModuleParameter" name="hostname" description="hostname/ip of the image" category="Output" mandatory="true" type="String" readonly="false"/>
                  </entry>
                  <entry>
                     <string><![CDATA[stratuslab.ram]]></string>
                     <parameter class="com.sixsq.slipstream.persistence.ModuleParameter" name="stratuslab.ram" description="Requested RAM (in GB)" category="stratuslab" mandatory="true" type="String" readonly="false"/>
                  </entry>
                  <entry>
                     <string><![CDATA[network]]></string>
                     <parameter class="com.sixsq.slipstream.persistence.ModuleParameter" name="network" description="Network type" category="Cloud" mandatory="true" type="Enum" readonly="false">
                        <value><![CDATA[Public]]></value>
                        <enumValues length="2">
                           <string>Public</string>
                           <string>Private</string>
                        </enumValues>
                     </parameter>
                  </entry>
                  <entry>
                     <string><![CDATA[cloudsigma.smp]]></string>
                     <parameter class="com.sixsq.slipstream.persistence.ModuleParameter" name="cloudsigma.smp" description="SMP (number of virtual CPUs)" category="cloudsigma" mandatory="true" type="String" readonly="false">
                        <value><![CDATA[1]]></value>
                     </parameter>
                  </entry>
                  <entry>
                     <string><![CDATA[dummy]]></string>
                     <parameter class="com.sixsq.slipstream.persistence.ModuleParameter" name="dummy" description="Placeholder for display" category="Input" mandatory="true" type="Dummy" readonly="false"/>
                  </entry>
                  <entry>
                     <string><![CDATA[cloudsigma.cpu]]></string>
                     <parameter class="com.sixsq.slipstream.persistence.ModuleParameter" name="cloudsigma.cpu" description="CPU in GHz" category="cloudsigma" mandatory="true" type="String" readonly="false">
                        <value><![CDATA[1]]></value>
                     </parameter>
                  </entry>
                  <entry>
                     <string><![CDATA[stratuslab.cpu]]></string>
                     <parameter class="com.sixsq.slipstream.persistence.ModuleParameter" name="stratuslab.cpu" description="Requested CPUs" category="stratuslab" mandatory="true" type="String" readonly="false"/>
                  </entry>
                  <entry>
                     <string><![CDATA[stratuslab.instance.type]]></string>
                     <parameter class="com.sixsq.slipstream.persistence.ModuleParameter" name="stratuslab.instance.type" description="Cloud instance type" category="stratuslab" mandatory="true" type="Enum" readonly="false">
                        <value><![CDATA[m1.small]]></value>
                        <enumValues length="8">
                           <string>inherited</string>
                           <string>m1.small</string>
                           <string>c1.medium</string>
                           <string>m1.large</string>
                           <string>m1.xlarge</string>
                           <string>c1.xlarge</string>
                           <string>t1.micro</string>
                           <string>standard.xsmall</string>
                        </enumValues>
                     </parameter>
                  </entry>
                  <entry>
                     <string><![CDATA[extra_disk_volatile]]></string>
                     <parameter class="com.sixsq.slipstream.persistence.ModuleParameter" name="extra_disk_volatile" description="Volatile extra disk in GB" category="Cloud" mandatory="true" type="String" readonly="false"/>
                  </entry>
                  <entry>
                     <string><![CDATA[instanceid]]></string>
                     <parameter class="com.sixsq.slipstream.persistence.ModuleParameter" name="instanceid" description="Cloud instance id" category="Output" mandatory="true" type="String" readonly="false"/>
                  </entry>
               </parameters>
               <authz owner="test" ownerGet="true" ownerPut="true" ownerPost="true" ownerDelete="true" ownerCreateChildren="true" groupGet="false" groupPut="false" groupPost="false" groupDelete="false" groupCreateChildren="false" publicGet="false" publicPut="false" publicPost="false" publicDelete="false" publicCreateChildren="false" inheritedGroupMembers="true">
                  <groupMembers class="java.util.ArrayList"/>
               </authz>
               <targets class="org.hibernate.collection.PersistentBag">
                  <target runInBackground="true" name="execute"><![CDATA[echo hello execute 1]]></target>
               </targets>
               <packages class="org.hibernate.collection.PersistentBag"/>
               <prerecipe><![CDATA[]]></prerecipe>
               <recipe><![CDATA[]]></recipe>
               <cloudImageIdentifiers class="org.hibernate.collection.PersistentBag">
                  <cloudImageIdentifier resourceUri="module/test/ubuntu/13/cloudsigma" cloudServiceName="cloudsigma" cloudImageIdentifier="d02ee717-33f7-478b-ba14-02196978fea8"/>
               </cloudImageIdentifiers>
               <extraDisks class="org.hibernate.collection.PersistentBag"/>
            </image>
         </node>
      </entry>
      <entry>
         <string>ubuntu2</string>
         <node deleted="false" name="ubuntu2" multiplicity="2" cloudService="bar" creation="2011-06-08 17:08:05.161 UTC">
            <image  lastModified="2012-12-17 10:30:11.259 CET" category="Image" deleted="false" resourceUri="module/test/ubuntu2/14" parentUri="module/test" name="test/ubuntu2" version="14" isBase="true" imageId="d02ee717-33f7-478b-ba14-0219
6978fea8" creation="2012-12-17 10:30:11.244 CET" shortName="ubuntu2" instanceType="inherited" loginUser="ubuntu" platform="ubuntu">
               <parameters class="org.hibernate.collection.PersistentMap">
                  <entry>
                    <string>extra.disk.volatile</string>
                    <parameter category="Cloud" class="com.sixsq.slipstream.persistence.ModuleParameter" description="" mandatory="true" name="extra.disk.volatile" readonly="false" type="String">
                      <value>foo</value>
                    </parameter>
                  </entry>
               </parameters>
               <targets class="org.hibernate.collection.PersistentBag">
                  <target runInBackground="true" name="execute"><![CDATA[echo hello execute 2]]></target>
               </targets>
            </image>
         </node>
      </entry>
   </nodes>
</module>
</run>
"""

USERPARAMETRS_XML = """<user deleted="false" resourceUri="user/test" name="test" email="test@sixsq.com" firstName="Test" lastName="User" organization="SixSq" issuper="false" state="ACTIVE" creation="2012-10-22 11:38:28.683 UTC">
   <parameters class="org.hibernate.collection.PersistentMap">
      <entry>
         <string><![CDATA[General.On Success Run Forever]]></string>
         <parameter class="com.sixsq.slipstream.persistence.UserParameter" name="General.On Success Run Forever" description="If no errors occur, keep the execution running. Useful for deployment or long tests." category="General" mandatory="true" type="Boolean" readonly="false">
            <value><![CDATA[on]]></value>
         </parameter>
      </entry>
      <entry>
         <string><![CDATA[StratusLab.endpoint]]></string>
         <parameter class="com.sixsq.slipstream.persistence.UserParameter" name="StratusLab.endpoint" description="" category="StratusLab" mandatory="true" type="String" readonly="false">
            <value><![CDATA[cloud.lal.stratuslab.eu]]></value>
         </parameter>
      </entry>
      <entry>
         <string><![CDATA[General.Verbosity Level]]></string>
         <parameter class="com.sixsq.slipstream.persistence.UserParameter" name="General.Verbosity Level" description="Level of verbosity. 0 - Actions, 1 - Steps, 2 - Details data, 3 - Debugging." category="General" mandatory="true" type="Enum" readonly="false">
            <value><![CDATA[3]]></value>
            <enumValues length="4">
               <string>0</string>
               <string>1</string>
               <string>2</string>
               <string>3</string>
            </enumValues>
         </parameter>
      </entry>
      <entry>
         <string><![CDATA[General.default_cloud_service]]></string>
         <parameter class="com.sixsq.slipstream.persistence.UserParameter" name="General.default_cloud_service" description="Select which cloud you want to use." category="General" mandatory="true" type="Enum" readonly="false">
            <value><![CDATA[StratusLab]]></value>
            <enumValues length="1">
               <string>StratusLab</string>
            </enumValues>
         </parameter>
      </entry>
      <entry>
         <string><![CDATA[StratusLab.ip.type]]></string>
         <parameter class="com.sixsq.slipstream.persistence.UserParameter" name="StratusLab.ip.type" description="IP type: public, local, private" category="StratusLab" mandatory="true" type="Enum" readonly="false">
            <value><![CDATA[public]]></value>
            <enumValues length="3">
               <string>public</string>
               <string>local</string>
               <string>private</string>
            </enumValues>
         </parameter>
      </entry>
      <entry>
         <string><![CDATA[General.On Error Run Forever]]></string>
         <parameter class="com.sixsq.slipstream.persistence.UserParameter" name="General.On Error Run Forever" description="If an error occurs, keep the execution running for investigation." category="General" mandatory="true" type="Boolean" readonly="false">
            <value><![CDATA[on]]></value>
         </parameter>
      </entry>
      <entry>
         <string><![CDATA[General.timeout]]></string>
         <parameter class="com.sixsq.slipstream.persistence.UserParameter" name="General.timeout" description="Minutes - When this timeout is reached, the execution is forcefully terminated." category="General" mandatory="true" type="String" readonly="false">
            <value><![CDATA[30]]></value>
         </parameter>
      </entry>
      <entry>
         <string><![CDATA[StratusLab.password]]></string>
         <parameter class="com.sixsq.slipstream.persistence.UserParameter" name="StratusLab.password" description="StratusLab account password" category="StratusLab" mandatory="true" type="Password" readonly="false">
            <value><![CDATA[UZgsxOjJSxA2]]></value>
         </parameter>
      </entry>
      <entry>
         <string><![CDATA[StratusLab.username]]></string>
         <parameter class="com.sixsq.slipstream.persistence.UserParameter" name="StratusLab.username" description="StratusLab account username" category="StratusLab" mandatory="true" type="RestrictedString" readonly="false">
            <value><![CDATA[sixsqdev]]></value>
         </parameter>
      </entry>
      <entry>
         <string><![CDATA[StratusLab.marketplace.endpoint]]></string>
         <parameter class="com.sixsq.slipstream.persistence.UserParameter" name="StratusLab.marketplace.endpoint" description="Default marketplace endpoint" category="StratusLab" mandatory="true" type="String" readonly="false">
            <value><![CDATA[http://marketplace.stratuslab.eu]]></value>
         </parameter>
      </entry>
      <entry>
         <string><![CDATA[General.ssh.public.key]]></string>
         <parameter class="com.sixsq.slipstream.persistence.UserParameter" name="General.ssh.public.key" description="SSH Public Key(s) (keys must be separated by new line)" category="General" mandatory="true" type="RestrictedText" readonly="false">
            <value><![CDATA[ssh-rsa abc]]></value>
         </parameter>
      </entry>
   </parameters>
</user>
"""


class SlipStreamHttpClientTestCase(unittest.TestCase):

    def setUp(self):
        self.context = {}
        self.context['diid'] = '1234'
        self.context['serviceurl'] = 'endpoint'
        self.context['username'] = 'username'
        self.context['password'] = 'password'
        self.context['nodename'] = 'ubuntu1'

    def tearDown(self):
        pass

    def test_getRunCategory(self):

        configHolder = ConfigHolder(config={'foo': 'bar'}, context=self.context)
        client = SlipStreamHttpClient(configHolder)
        client._httpGet = Mock(return_value=(200, '<run category="foo" />'))

        self.assertEquals('foo', client.getRunCategory())
        self.assertEquals('foo', client.getRunCategory())

        self.assertEquals(1, client._httpGet.call_count)

    def test_getDeploymentTargets(self):
        targets = DomExtractor.getDeploymentTargets(etree.fromstring(RUN_XML),
                                                    'ubuntu1')
        self.assertEquals('echo hello execute 1', targets['execute'][0])
        self.assertEquals(True, targets['execute'][1])

        targets = DomExtractor.getDeploymentTargets(etree.fromstring(RUN_XML),
                                                    'ubuntu2')
        self.assertEquals('echo hello execute 2', targets['execute'][0])
        self.assertEquals(True, targets['execute'][1])

        for image_dom in etree.fromstring(RUN_XML).findall('module/nodes/entry/node/image'):
            targets = DomExtractor.getDeploymentTargetsFromImageDom(image_dom)
            if image_dom.attrib['name'] == 'test/ubuntu1':
                self.assertEquals('echo hello execute 1', targets['execute'][0])
                self.assertEquals(True, targets['execute'][1])
            elif image_dom.attrib['name'] == 'test/ubuntu2':
                self.assertEquals('echo hello execute 2', targets['execute'][0])
                self.assertEquals(True, targets['execute'][1])

    def test_extractNodesFromDeployment(self):
        nodes = DomExtractor.extractNodesFromRun(etree.fromstring(RUN_XML))
        self.assertEquals(2, len(nodes))
        for node in nodes:
            assert isinstance(node['image'], ElementTree._Element)
            if node['nodename'] == 'ubuntu1':
                self.assertEquals(1, node['multiplicity'])
                self.assertEquals('foo', node['cloudService'])
            elif node['nodename'] == 'ubuntu2':
                self.assertEquals(2, node['multiplicity'])
                self.assertEquals('bar', node['cloudService'])

    def test_getBuildTargetsFromImageModule(self):
        package1 = 'vim-enhanced'
        package2 = 'yum-utils'
        prerecipe = 'echo prerecipe'
        recipe = 'echo recipe'

        image_module_xml = """<imageModule>
   <targets class="org.hibernate.collection.PersistentBag"/>
   <packages class="org.hibernate.collection.PersistentBag">
      <package name="%(package1)s"/>
      <package name="%(package2)s"/>
   </packages>
   <prerecipe><![CDATA[%(prerecipe)s]]></prerecipe>
   <recipe><![CDATA[%(recipe)s]]></recipe>
</imageModule>
""" % {'package1': package1,
       'package2': package2,
       'prerecipe': prerecipe,
       'recipe': recipe}

        dom = etree.fromstring(image_module_xml)
        targets = DomExtractor.getBuildTargets(dom)

        failMsg = "Failure getting '%s' build target."
        assert targets['prerecipe'] == prerecipe, failMsg % 'prerecipe'
        assert targets['recipe'] == recipe, failMsg % 'recipe'
        assert isinstance(targets['packages'], list), failMsg % 'packages'
        assert package1 in targets['packages'], failMsg % 'packages'
        assert package2 in targets['packages'], failMsg % 'packages'

    def test_getExtraDisks(self):
        for node_dom in etree.fromstring(RUN_XML).findall('module/nodes/entry/node'):
            image_dom = node_dom.find('image')
            extra_disks = DomExtractor.getExtraDisksFromImageDom(image_dom)
            if node_dom.get('name') == 'ubuntu1':
                assert extra_disks == {}
            elif node_dom.get('name') == 'ubuntu2':
                assert extra_disks['extra.disk.volatile'] == 'foo'

    def test_getUserInfoUser(self):
        client = SlipStreamHttpClient(ConfigHolder(config={'foo': 'bar'},
                                                   context=self.context))
        client._getUserContent = Mock(return_value=USERPARAMETRS_XML)
        userInfo = client.getUserInfo('')
        assert 'Test' == userInfo.get_user('firstName')
        assert 'User' == userInfo.get_user('lastName')
        assert 'test@sixsq.com' == userInfo.get_user('email')

    def test_getUserInfo(self):
        client = SlipStreamHttpClient(ConfigHolder(config={'foo': 'bar'},
                                                   context=self.context))
        client._getUserContent = Mock(return_value=USERPARAMETRS_XML)
        userInfo = client.getUserInfo('StratusLab')

        assert 'test@sixsq.com' == userInfo.get_user('email')

        assert 'cloud.lal.stratuslab.eu' == userInfo.get_cloud('endpoint')
        assert 'public' == userInfo.get_cloud('ip.type')
        assert 'ssh-rsa abc' == userInfo.get_general('ssh.public.key')

        assert 'on' == userInfo.get_general('On Error Run Forever')
        assert '3' == userInfo.get_general('Verbosity Level')

    def test_cpuRamNetwork(self):
        client = SlipStreamHttpClient(ConfigHolder(context=self.context,
                                                   config={'foo': 'bar'}))
        client._httpGet = Mock(return_value=(200, RUN_XML))

        nodes = client.getNodesInfo()

        assert nodes[0]['image']['cloud_parameters']['stratuslab']['stratuslab.cpu'] is None
        assert nodes[0]['image']['cloud_parameters']['stratuslab']['stratuslab.ram'] is None
        assert nodes[0]['image']['cloud_parameters']['cloudsigma']['cloudsigma.ram'] == '1'
        assert nodes[0]['image']['cloud_parameters']['cloudsigma']['cloudsigma.cpu'] == '1'
        assert nodes[0]['image']['cloud_parameters']['cloudsigma']['cloudsigma.smp'] == '1'
        assert nodes[0]['image']['cloud_parameters']['stratuslab']['stratuslab.instance.type'] == 'm1.small'
        assert nodes[0]['image']['cloud_parameters']['Cloud']['network'] == 'Public'

    def test_getRemoteNodes(self):
        client = SlipStreamHttpClient(ConfigHolder(context=self.context,
                                                   config={'foo': 'bar'}))
        client._httpGet = Mock(return_value=(200, RUN_XML))

        nodes = client.getNodesInfo()
        assert len(nodes) == 2

        node_kyes = ['cloudService', 'multiplicity', 'nodename', 'image']
        for node in nodes:
            for key in node_kyes:
                self.assertTrue(key in node, 'No element %s' % key)

if __name__ == '__main__':
    unittest.main()

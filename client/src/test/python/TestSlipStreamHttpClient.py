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

RUN_XML = """<run category="Deployment" deleted="false" resourceUri="run/03ea004e-0089-4bb5-a3f4-849bcd1272c8" uuid="03ea004e-0089-4bb5-a3f4-849bcd1272c8" type="Orchestration" cloudServiceName="myCloud" cloudServiceNames="myCloud" state="Done" moduleResourceUri="module/examples/tutorials/service-testing/system/72" startTime="2014-07-07 13:47:20.189 CEST" endTime="2014-07-07 14:03:42.709 CEST" nodeNames="apache.1,testclient.1,testclient.2,orchestrator-myCloud" user="super" mutable="false" creation="2014-07-07 13:47:20.189 CEST" groups="myCloud:apache, myCloud:testclient, myCloud:testclient, ">
   <parameters class="org.hibernate.collection.internal.PersistentMap">
      <entry>
         <string><![CDATA[apache--cloudservice]]></string>
         <parameter class="com.sixsq.slipstream.persistence.RunParameter" name="apache--cloudservice" description="Cloud Service where the node resides" category="General" mandatory="false" type="String" readonly="false" order_="0" order="0">
            <value><![CDATA[myCloud]]></value>
         </parameter>
      </entry>
      <entry>
         <string><![CDATA[testclient--multiplicity]]></string>
         <parameter class="com.sixsq.slipstream.persistence.RunParameter" name="testclient--multiplicity" description="Multiplicity number" category="General" mandatory="false" type="String" readonly="false" order_="0" order="0">
            <value><![CDATA[2]]></value>
         </parameter>
      </entry>
      <entry>
         <string><![CDATA[testclient--cloudservice]]></string>
         <parameter class="com.sixsq.slipstream.persistence.RunParameter" name="testclient--cloudservice" description="Cloud Service where the node resides" category="General" mandatory="false" type="String" readonly="false" order_="0" order="0">
            <value><![CDATA[myCloud]]></value>
         </parameter>
      </entry>
      <entry>
         <string><![CDATA[General.On Error Run Forever]]></string>
         <parameter class="com.sixsq.slipstream.persistence.RunParameter" name="General.On Error Run Forever" description="If an error occurs, keep the execution running for investigation." category="General" mandatory="false" type="String" readonly="false" order_="0" order="0">
            <value><![CDATA[true]]></value>
         </parameter>
      </entry>
      <entry>
         <string><![CDATA[garbage_collected]]></string>
         <parameter class="com.sixsq.slipstream.persistence.RunParameter" name="garbage_collected" description="true if the Run was already garbage collected" category="General" mandatory="false" type="String" readonly="false" order_="0" order="0">
            <value><![CDATA[false]]></value>
         </parameter>
      </entry>
      <entry>
         <string><![CDATA[General.On Success Run Forever]]></string>
         <parameter class="com.sixsq.slipstream.persistence.RunParameter" name="General.On Success Run Forever" description="If no errors occur, keep the execution running. Useful for deployment or long tests." category="General" mandatory="false" type="String" readonly="false" order_="0" order="0">
            <value><![CDATA[true]]></value>
         </parameter>
      </entry>
      <entry>
         <string><![CDATA[apache--multiplicity]]></string>
         <parameter class="com.sixsq.slipstream.persistence.RunParameter" name="apache--multiplicity" description="Multiplicity number" category="General" mandatory="false" type="String" readonly="false" order_="0" order="0">
            <value><![CDATA[1]]></value>
         </parameter>
      </entry>
   </parameters>
   <runtimeParameters class="org.hibernate.collection.internal.PersistentMap">
      <entry>
         <string><![CDATA[testclient.2:webserver.ready]]></string>
         <runtimeParameter description="Server ready to recieve connections" deleted="false" key="testclient.2:webserver.ready" isSet="true" group="testclient.2" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.210 CEST"><![CDATA[true]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[testclient.2:network]]></string>
         <runtimeParameter description="Network type" deleted="false" key="testclient.2:network" isSet="true" group="testclient.2" mapsOthers="false" type="Enum" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.210 CEST"><![CDATA[Private]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[testclient.1:id]]></string>
         <runtimeParameter description="Node instance id" deleted="false" key="testclient.1:id" isSet="true" group="testclient.1" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.205 CEST"><![CDATA[1]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[apache.1:abort]]></string>
         <runtimeParameter description="Machine abort flag, set when aborting" deleted="false" key="apache.1:abort" isSet="false" group="apache.1" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.200 CEST"><![CDATA[]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[testclient.1:instanceid]]></string>
         <runtimeParameter description="Cloud instance id" deleted="false" key="testclient.1:instanceid" isSet="true" group="testclient.1" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.210 CEST"><![CDATA[2a4fd2ee-1f2a-45ac-affd-896d5def8115]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[apache.1:hostname]]></string>
         <runtimeParameter description="hostname/ip of the image" deleted="false" key="apache.1:hostname" isSet="true" group="apache.1" mapsOthers="true" type="String" mappedRuntimeParameterNames="testclient.1:webserver.hostname,testclient.2:webserver.hostname," isMappedValue="false" creation="2014-07-07 13:47:20.205 CEST"><![CDATA[192.168.1.10]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[apache.1:cloudservice]]></string>
         <runtimeParameter description="Cloud Service where the node resides" deleted="false" key="apache.1:cloudservice" isSet="true" group="apache.1" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.200 CEST"><![CDATA[myCloud]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[apache.1:instanceid]]></string>
         <runtimeParameter description="Cloud instance id" deleted="false" key="apache.1:instanceid" isSet="true" group="apache.1" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.204 CEST"><![CDATA[c72357ea-46f8-4d27-a48c-aa93762ae5ba]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[ss:category]]></string>
         <runtimeParameter description="Module category" deleted="false" key="ss:category" isSet="true" group="Global" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.199 CEST"><![CDATA[Deployment]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[apache.1:ready]]></string>
         <runtimeParameter description="Server ready to recieve connections" deleted="false" key="apache.1:ready" isSet="true" group="apache.1" mapsOthers="true" type="String" mappedRuntimeParameterNames="testclient.1:webserver.ready,testclient.2:webserver.ready," isMappedValue="false" creation="2014-07-07 13:47:20.205 CEST"><![CDATA[true]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[orchestrator-myCloud:hostname]]></string>
         <runtimeParameter description="hostname/ip of the image" deleted="false" key="orchestrator-myCloud:hostname" isSet="true" group="orchestrator-myCloud" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.211 CEST"><![CDATA[ 192.168.1.9]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[testclient.1:nodename]]></string>
         <runtimeParameter description="Nodename" deleted="false" key="testclient.1:nodename" isSet="true" group="testclient.1" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.205 CEST"><![CDATA[testclient]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[testclient.2:cloudservice]]></string>
         <runtimeParameter description="Cloud Service where the node resides" deleted="false" key="testclient.2:cloudservice" isSet="true" group="testclient.2" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.210 CEST"><![CDATA[myCloud]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[orchestrator-myCloud:is.orchestrator]]></string>
         <runtimeParameter description="True if it&apos;s an orchestrator" deleted="false" key="orchestrator-myCloud:is.orchestrator" isSet="true" group="orchestrator-myCloud" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.211 CEST"><![CDATA[true]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[testclient.2:webserver.port]]></string>
         <runtimeParameter description="Port on which the web server listens" deleted="false" key="testclient.2:webserver.port" isSet="true" group="testclient.2" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.210 CEST"><![CDATA[8080]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[testclient.1:url.service]]></string>
         <runtimeParameter description="Optional service URL for virtual machine" deleted="false" key="testclient.1:url.service" isSet="false" group="testclient.1" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.205 CEST"><![CDATA[]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[apache.1:extra.disk.volatile]]></string>
         <runtimeParameter description="Volatile extra disk in GB" deleted="false" key="apache.1:extra.disk.volatile" isSet="false" group="apache.1" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.205 CEST"/>
      </entry>
      <entry>
         <string><![CDATA[orchestrator-myCloud:statecustom]]></string>
         <runtimeParameter description="Custom state" deleted="false" key="orchestrator-myCloud:statecustom" isSet="false" group="orchestrator-myCloud" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.210 CEST"><![CDATA[]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[testclient.1:is.orchestrator]]></string>
         <runtimeParameter description="True if it&apos;s an orchestrator" deleted="false" key="testclient.1:is.orchestrator" isSet="true" group="testclient.1" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.205 CEST"><![CDATA[false]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[testclient.1:myCloud.security.groups]]></string>
         <runtimeParameter description="Security Groups (comma separated list)" deleted="false" key="testclient.1:myCloud.security.groups" isSet="true" group="testclient.1" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.210 CEST"><![CDATA[default]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[ss:recovery.mode]]></string>
         <runtimeParameter description="Run abort flag, set when aborting" deleted="false" key="ss:recovery.mode" isSet="true" group="Global" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.199 CEST"><![CDATA[false]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[testclient.1:vmstate]]></string>
         <runtimeParameter description="State of the VM, according to the cloud layer" deleted="false" key="testclient.1:vmstate" isSet="true" group="testclient.1" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.205 CEST"><![CDATA[Unknown]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[testclient.2:statecustom]]></string>
         <runtimeParameter description="Custom state" deleted="false" key="testclient.2:statecustom" isSet="true" group="testclient.2" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.210 CEST"><![CDATA[OK: Hello from Apache deployed by SlipStream!]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[ss:abort]]></string>
         <runtimeParameter description="Run abort flag, set when aborting" deleted="false" key="ss:abort" isSet="false" group="Global" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.199 CEST"><![CDATA[]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[testclient.2:abort]]></string>
         <runtimeParameter description="Machine abort flag, set when aborting" deleted="false" key="testclient.2:abort" isSet="false" group="testclient.2" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.210 CEST"><![CDATA[]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[apache.1:scale.state]]></string>
         <runtimeParameter description="Defined scalability state" deleted="false" key="apache.1:scale.state" isSet="true" group="apache.1" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.204 CEST"><![CDATA[operational]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[testclient.2:hostname]]></string>
         <runtimeParameter description="hostname/ip of the image" deleted="false" key="testclient.2:hostname" isSet="true" group="testclient.2" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.210 CEST"><![CDATA[192.168.1.11]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[testclient.1:url.ssh]]></string>
         <runtimeParameter description="SSH URL to connect to virtual machine" deleted="false" key="testclient.1:url.ssh" isSet="true" group="testclient.1" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.205 CEST"><![CDATA[ssh://root@192.168.1.12]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[orchestrator-myCloud:max.iaas.workers]]></string>
         <runtimeParameter description="Max number of concurrently provisioned VMs by orchestrator" deleted="false" key="orchestrator-myCloud:max.iaas.workers" isSet="true" group="orchestrator-myCloud" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.211 CEST"><![CDATA[20]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[ss:tags]]></string>
         <runtimeParameter description="Comma separated tag values" deleted="false" key="ss:tags" isSet="false" group="Global" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.199 CEST"><![CDATA[]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[testclient.2:extra.disk.volatile]]></string>
         <runtimeParameter description="Volatile extra disk in GB" deleted="false" key="testclient.2:extra.disk.volatile" isSet="false" group="testclient.2" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.210 CEST"/>
      </entry>
      <entry>
         <string><![CDATA[orchestrator-myCloud:instanceid]]></string>
         <runtimeParameter description="Cloud instance id" deleted="false" key="orchestrator-myCloud:instanceid" isSet="true" group="orchestrator-myCloud" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.211 CEST"><![CDATA[ec7c2dcc-88db-4bd9-8717-6dd3eef4d186]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[apache.1:nodename]]></string>
         <runtimeParameter description="Nodename" deleted="false" key="apache.1:nodename" isSet="true" group="apache.1" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.200 CEST"><![CDATA[apache]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[apache.1:myCloud.instance.type]]></string>
         <runtimeParameter description="Instance type (flavor)" deleted="false" key="apache.1:myCloud.instance.type" isSet="true" group="apache.1" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.205 CEST"><![CDATA[m1.tiny]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[ss:groups]]></string>
         <runtimeParameter description="Comma separated node groups" deleted="false" key="ss:groups" isSet="true" group="Global" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.199 CEST"><![CDATA[myCloud:apache, myCloud:testclient, myCloud:testclient, ]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[apache.1:url.ssh]]></string>
         <runtimeParameter description="SSH URL to connect to virtual machine" deleted="false" key="apache.1:url.ssh" isSet="true" group="apache.1" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.200 CEST"><![CDATA[ssh://root@192.168.1.10]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[testclient.2:myCloud.security.groups]]></string>
         <runtimeParameter description="Security Groups (comma separated list)" deleted="false" key="testclient.2:myCloud.security.groups" isSet="true" group="testclient.2" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.210 CEST"><![CDATA[default]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[apache:multiplicity]]></string>
         <runtimeParameter description="Multiplicity number" deleted="false" key="apache:multiplicity" isSet="true" group="apache" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.210 CEST"><![CDATA[1]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[apache.1:is.orchestrator]]></string>
         <runtimeParameter description="True if it&apos;s an orchestrator" deleted="false" key="apache.1:is.orchestrator" isSet="true" group="apache.1" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.200 CEST"><![CDATA[false]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[testclient.1:webserver.hostname]]></string>
         <runtimeParameter description="Server hostname" deleted="false" key="testclient.1:webserver.hostname" isSet="true" group="testclient.1" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.210 CEST"><![CDATA[192.168.1.10]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[testclient.2:complete]]></string>
         <runtimeParameter description="&apos;true&apos; when current state is completed" deleted="false" key="testclient.2:complete" isSet="true" group="testclient.2" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.210 CEST"><![CDATA[false]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[testclient.2:url.service]]></string>
         <runtimeParameter description="Optional service URL for virtual machine" deleted="false" key="testclient.2:url.service" isSet="false" group="testclient.2" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.210 CEST"><![CDATA[]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[testclient.1:complete]]></string>
         <runtimeParameter description="&apos;true&apos; when current state is completed" deleted="false" key="testclient.1:complete" isSet="true" group="testclient.1" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.205 CEST"><![CDATA[false]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[testclient.1:myCloud.instance.type]]></string>
         <runtimeParameter description="Instance type (flavor)" deleted="false" key="testclient.1:myCloud.instance.type" isSet="true" group="testclient.1" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.210 CEST"><![CDATA[m1.tiny]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[testclient.1:cloudservice]]></string>
         <runtimeParameter description="Cloud Service where the node resides" deleted="false" key="testclient.1:cloudservice" isSet="true" group="testclient.1" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.205 CEST"><![CDATA[myCloud]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[apache.1:url.service]]></string>
         <runtimeParameter description="Optional service URL for virtual machine" deleted="false" key="apache.1:url.service" isSet="true" group="apache.1" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.200 CEST"><![CDATA[http://192.168.1.10:8080]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[apache.1:myCloud.security.groups]]></string>
         <runtimeParameter description="Security Groups (comma separated list)" deleted="false" key="apache.1:myCloud.security.groups" isSet="true" group="apache.1" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.205 CEST"><![CDATA[default]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[apache.1:id]]></string>
         <runtimeParameter description="Node instance id" deleted="false" key="apache.1:id" isSet="true" group="apache.1" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.200 CEST"><![CDATA[1]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[testclient.2:webserver.hostname]]></string>
         <runtimeParameter description="Server hostname" deleted="false" key="testclient.2:webserver.hostname" isSet="true" group="testclient.2" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.210 CEST"><![CDATA[192.168.1.10]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[ss:url.service]]></string>
         <runtimeParameter description="Optional service URL for the deployment" deleted="false" key="ss:url.service" isSet="true" group="Global" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.199 CEST"><![CDATA[http://192.168.1.10:8080]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[apache:ids]]></string>
         <runtimeParameter description="IDs of the machines in a mutable deployment." deleted="false" key="apache:ids" isSet="true" group="apache" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.210 CEST"><![CDATA[1]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[orchestrator-myCloud:abort]]></string>
         <runtimeParameter description="Machine abort flag, set when aborting" deleted="false" key="orchestrator-myCloud:abort" isSet="false" group="orchestrator-myCloud" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.210 CEST"><![CDATA[]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[testclient.1:statecustom]]></string>
         <runtimeParameter description="Custom state" deleted="false" key="testclient.1:statecustom" isSet="true" group="testclient.1" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.205 CEST"><![CDATA[OK: Hello from Apache deployed by SlipStream!]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[ss:state]]></string>
         <runtimeParameter description="Global execution state" deleted="false" key="ss:state" isSet="true" group="Global" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.199 CEST"><![CDATA[Done]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[testclient.2:scale.state]]></string>
         <runtimeParameter description="Defined scalability state" deleted="false" key="testclient.2:scale.state" isSet="true" group="testclient.2" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.210 CEST"><![CDATA[operational]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[testclient.2:myCloud.instance.type]]></string>
         <runtimeParameter description="Instance type (flavor)" deleted="false" key="testclient.2:myCloud.instance.type" isSet="true" group="testclient.2" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.210 CEST"><![CDATA[m1.tiny]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[apache.1:vmstate]]></string>
         <runtimeParameter description="State of the VM, according to the cloud layer" deleted="false" key="apache.1:vmstate" isSet="true" group="apache.1" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.200 CEST"><![CDATA[Unknown]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[testclient.1:extra.disk.volatile]]></string>
         <runtimeParameter description="Volatile extra disk in GB" deleted="false" key="testclient.1:extra.disk.volatile" isSet="false" group="testclient.1" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.210 CEST"/>
      </entry>
      <entry>
         <string><![CDATA[testclient.1:webserver.port]]></string>
         <runtimeParameter description="Port on which the web server listens" deleted="false" key="testclient.1:webserver.port" isSet="true" group="testclient.1" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.210 CEST"><![CDATA[8080]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[orchestrator-myCloud:url.service]]></string>
         <runtimeParameter description="Optional service URL for virtual machine" deleted="false" key="orchestrator-myCloud:url.service" isSet="false" group="orchestrator-myCloud" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.211 CEST"><![CDATA[]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[apache.1:network]]></string>
         <runtimeParameter description="Network type" deleted="false" key="apache.1:network" isSet="true" group="apache.1" mapsOthers="false" type="Enum" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.205 CEST"><![CDATA[Private]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[testclient.2:id]]></string>
         <runtimeParameter description="Node instance id" deleted="false" key="testclient.2:id" isSet="true" group="testclient.2" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.210 CEST"><![CDATA[2]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[apache.1:complete]]></string>
         <runtimeParameter description="&apos;true&apos; when current state is completed" deleted="false" key="apache.1:complete" isSet="true" group="apache.1" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.200 CEST"><![CDATA[false]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[testclient.1:image.id]]></string>
         <runtimeParameter description="Cloud image id" deleted="false" key="testclient.1:image.id" isSet="true" group="testclient.1" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.210 CEST"><![CDATA[71651c3f-92de-4b75-b5f4-0bcfbf3b61c2]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[apache.1:image.id]]></string>
         <runtimeParameter description="Cloud image id" deleted="false" key="apache.1:image.id" isSet="true" group="apache.1" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.204 CEST"><![CDATA[71651c3f-92de-4b75-b5f4-0bcfbf3b61c2]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[orchestrator-myCloud:url.ssh]]></string>
         <runtimeParameter description="SSH URL to connect to virtual machine" deleted="false" key="orchestrator-myCloud:url.ssh" isSet="true" group="orchestrator-myCloud" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.210 CEST"><![CDATA[ssh://root@192.168.1.9]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[orchestrator-myCloud:vmstate]]></string>
         <runtimeParameter description="State of the VM, according to the cloud layer" deleted="false" key="orchestrator-myCloud:vmstate" isSet="true" group="orchestrator-myCloud" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.210 CEST"><![CDATA[Unknown]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[testclient.2:image.id]]></string>
         <runtimeParameter description="Cloud image id" deleted="false" key="testclient.2:image.id" isSet="true" group="testclient.2" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.210 CEST"><![CDATA[71651c3f-92de-4b75-b5f4-0bcfbf3b61c2]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[testclient.1:abort]]></string>
         <runtimeParameter description="Machine abort flag, set when aborting" deleted="false" key="testclient.1:abort" isSet="false" group="testclient.1" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.205 CEST"><![CDATA[]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[testclient.2:nodename]]></string>
         <runtimeParameter description="Nodename" deleted="false" key="testclient.2:nodename" isSet="true" group="testclient.2" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.210 CEST"><![CDATA[testclient]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[testclient.1:webserver.ready]]></string>
         <runtimeParameter description="Server ready to recieve connections" deleted="false" key="testclient.1:webserver.ready" isSet="true" group="testclient.1" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.210 CEST"><![CDATA[true]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[testclient:multiplicity]]></string>
         <runtimeParameter description="Multiplicity number" deleted="false" key="testclient:multiplicity" isSet="true" group="testclient" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.210 CEST"><![CDATA[2]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[testclient.2:url.ssh]]></string>
         <runtimeParameter description="SSH URL to connect to virtual machine" deleted="false" key="testclient.2:url.ssh" isSet="true" group="testclient.2" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.210 CEST"><![CDATA[ssh://root@192.168.1.11]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[testclient.1:scale.state]]></string>
         <runtimeParameter description="Defined scalability state" deleted="false" key="testclient.1:scale.state" isSet="true" group="testclient.1" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.210 CEST"><![CDATA[operational]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[testclient:ids]]></string>
         <runtimeParameter description="IDs of the machines in a mutable deployment." deleted="false" key="testclient:ids" isSet="true" group="testclient" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.210 CEST"><![CDATA[1,2]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[testclient.2:vmstate]]></string>
         <runtimeParameter description="State of the VM, according to the cloud layer" deleted="false" key="testclient.2:vmstate" isSet="true" group="testclient.2" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.210 CEST"><![CDATA[Unknown]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[testclient.1:network]]></string>
         <runtimeParameter description="Network type" deleted="false" key="testclient.1:network" isSet="true" group="testclient.1" mapsOthers="false" type="Enum" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.210 CEST"><![CDATA[Private]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[apache.1:statecustom]]></string>
         <runtimeParameter description="Custom state" deleted="false" key="apache.1:statecustom" isSet="false" group="apache.1" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.200 CEST"><![CDATA[]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[apache.1:port]]></string>
         <runtimeParameter description="Port" deleted="false" key="apache.1:port" isSet="true" group="apache.1" mapsOthers="true" type="String" mappedRuntimeParameterNames="testclient.1:webserver.port,testclient.2:webserver.port," isMappedValue="false" creation="2014-07-07 13:47:20.205 CEST"><![CDATA[8080]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[orchestrator-myCloud:complete]]></string>
         <runtimeParameter description="&apos;true&apos; when current state is completed" deleted="false" key="orchestrator-myCloud:complete" isSet="true" group="orchestrator-myCloud" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.210 CEST"><![CDATA[false]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[testclient.2:instanceid]]></string>
         <runtimeParameter description="Cloud instance id" deleted="false" key="testclient.2:instanceid" isSet="true" group="testclient.2" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.210 CEST"><![CDATA[5cdce3b3-e0de-4b28-8481-e30454293199]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[testclient.1:hostname]]></string>
         <runtimeParameter description="hostname/ip of the image" deleted="false" key="testclient.1:hostname" isSet="true" group="testclient.1" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.210 CEST"><![CDATA[192.168.1.12]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[testclient.2:is.orchestrator]]></string>
         <runtimeParameter description="True if it&apos;s an orchestrator" deleted="false" key="testclient.2:is.orchestrator" isSet="true" group="testclient.2" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.210 CEST"><![CDATA[false]]></runtimeParameter>
      </entry>
      <entry>
         <string><![CDATA[orchestrator-myCloud:cloudservice]]></string>
         <runtimeParameter description="Cloud Service where the node resides" deleted="false" key="orchestrator-myCloud:cloudservice" isSet="true" group="orchestrator-myCloud" mapsOthers="false" type="String" mappedRuntimeParameterNames="" isMappedValue="false" creation="2014-07-07 13:47:20.211 CEST"><![CDATA[myCloud]]></runtimeParameter>
      </entry>
   </runtimeParameters>
   <module class="com.sixsq.slipstream.persistence.DeploymentModule" lastModified="2014-07-04 02:21:08.16 CEST" category="Deployment" description="Deployment binding the apache server and the test client node(s)." deleted="false" resourceUri="module/examples/tutorials/service-testing/system/72" parentUri="module/examples/tutorials/service-testing" name="examples/tutorials/service-testing/system" version="72" isLatestVersion="true" logoLink="" creation="2014-05-21 10:49:08.291 CEST" shortName="system">
      <parameters class="org.hibernate.collection.internal.PersistentMap"/>
      <authz owner="super" ownerGet="true" ownerPut="true" ownerPost="true" ownerDelete="true" ownerCreateChildren="true" groupGet="true" groupPut="true" groupPost="true" groupDelete="false" groupCreateChildren="false" publicGet="true" publicPut="false" publicPost="true" publicDelete="false" publicCreateChildren="false" inheritedGroupMembers="true">
         <groupMembers class="java.util.ArrayList"/>
      </authz>
      <commit author="super">
         <comment></comment>
      </commit>
      <nodes class="org.hibernate.collection.internal.PersistentMap">
         <entry>
            <string>apache</string>
            <node deleted="false" name="apache" multiplicity="1" cloudService="myCloud" imageUri="module/examples/tutorials/service-testing/apache" creation="2014-07-04 02:21:07.980 CEST" network="Private">
               <parameters class="org.hibernate.collection.internal.PersistentMap"/>
               <parameterMappings class="org.hibernate.collection.internal.PersistentMap"/>
               <image lastModified="2014-07-04 01:02:27.113 CEST" category="Image" description="Apache web server appliance with custom landing page." deleted="false" resourceUri="module/examples/tutorials/service-testing/apache/71" parentUri="module/examples/tutorials/service-testing" name="examples/tutorials/service-testing/apache" version="71" isLatestVersion="true" moduleReferenceUri="module/examples/images/ubuntu-12.04" logoLink="http://pegasosdi.uab.es/geoportal/images/Apache_HTTP_server_transparente.png" isBase="false" imageId="71651c3f-92de-4b75-b5f4-0bcfbf3b61c2" creation="2014-05-21 10:41:46.451 CEST" shortName="apache" loginUser="" platform="ubuntu">
                  <parameters class="org.hibernate.collection.internal.PersistentMap">
                     <entry>
                        <string><![CDATA[instanceid]]></string>
                        <parameter class="com.sixsq.slipstream.persistence.ModuleParameter" name="instanceid" description="Cloud instance id" category="Output" mandatory="true" type="String" readonly="false" order_="0" isSet="false" order="0"/>
                     </entry>
                     <entry>
                        <string><![CDATA[nuvlabox.disks.bus.type]]></string>
                        <parameter class="com.sixsq.slipstream.persistence.ModuleParameter" name="nuvlabox.disks.bus.type" description="VM disks bus type" category="nuvlabox" mandatory="true" type="Enum" readonly="false" order_="0" isSet="true" order="0">
                           <enumValues length="2">
                              <string>virtio</string>
                              <string>scsi</string>
                           </enumValues>
                           <value><![CDATA[virtio]]></value>
                           <defaultValue><![CDATA[virtio]]></defaultValue>
                        </parameter>
                     </entry>
                     <entry>
                        <string><![CDATA[port]]></string>
                        <parameter class="com.sixsq.slipstream.persistence.ModuleParameter" name="port" description="Port" category="Output" mandatory="false" type="String" readonly="false" order_="0" isSet="true" order="0">
                           <value><![CDATA[8080]]></value>
                           <defaultValue><![CDATA[8080]]></defaultValue>
                        </parameter>
                     </entry>
                     <entry>
                        <string><![CDATA[extra.disk.volatile]]></string>
                        <parameter class="com.sixsq.slipstream.persistence.ModuleParameter" name="extra.disk.volatile" description="Volatile extra disk in GB" category="Cloud" mandatory="true" type="String" readonly="false" order_="0" isSet="false" order="0"/>
                     </entry>
                     <entry>
                        <string><![CDATA[myCloud.instance.type]]></string>
                        <parameter class="com.sixsq.slipstream.persistence.ModuleParameter" name="myCloud.instance.type" description="Instance type (flavor)" category="myCloud" mandatory="true" type="String" readonly="false" order_="0" isSet="true" order="0">
                           <value><![CDATA[m1.tiny]]></value>
                           <defaultValue><![CDATA[m1.tiny]]></defaultValue>
                        </parameter>
                     </entry>
                     <entry>
                        <string><![CDATA[InterouteV2.networks]]></string>
                        <parameter class="com.sixsq.slipstream.persistence.ModuleParameter" name="InterouteV2.networks" description="List of networks (comma separated)" category="InterouteV2" mandatory="true" type="String" readonly="false" order_="0" isSet="true" order="0">
                           <value><![CDATA[HNEB0_IPACP]]></value>
                           <defaultValue><![CDATA[HNEB0_IPACP]]></defaultValue>
                        </parameter>
                     </entry>
                     <entry>
                        <string><![CDATA[nuvlabox.cpu]]></string>
                        <parameter class="com.sixsq.slipstream.persistence.ModuleParameter" name="nuvlabox.cpu" description="cpu" category="nuvlabox" mandatory="true" type="String" readonly="false" order_="0" isSet="true" order="0">
                           <value><![CDATA[1]]></value>
                           <defaultValue><![CDATA[1]]></defaultValue>
                        </parameter>
                     </entry>
                     <entry>
                        <string><![CDATA[network]]></string>
                        <parameter class="com.sixsq.slipstream.persistence.ModuleParameter" name="network" description="Network type" category="Cloud" mandatory="true" type="Enum" readonly="false" order_="0" isSet="true" order="0">
                           <enumValues length="2">
                              <string>Public</string>
                              <string>Private</string>
                           </enumValues>
                           <value><![CDATA[Private]]></value>
                           <defaultValue><![CDATA[Private]]></defaultValue>
                        </parameter>
                     </entry>
                     <entry>
                        <string><![CDATA[InterouteV2.instance.type]]></string>
                        <parameter class="com.sixsq.slipstream.persistence.ModuleParameter" name="InterouteV2.instance.type" description="Instance type (flavor)" category="InterouteV2" mandatory="true" type="String" readonly="false" order_="0" isSet="true" order="0">
                           <value><![CDATA[512-1]]></value>
                           <defaultValue><![CDATA[512-1]]></defaultValue>
                        </parameter>
                     </entry>
                     <entry>
                        <string><![CDATA[nuvlabox.instance.type]]></string>
                        <parameter class="com.sixsq.slipstream.persistence.ModuleParameter" name="nuvlabox.instance.type" description="Cloud instance type" category="nuvlabox" mandatory="true" type="Enum" readonly="false" order_="0" isSet="true" order="0">
                           <enumValues length="7">
                              <string>m1.small</string>
                              <string>c1.medium</string>
                              <string>m1.large</string>
                              <string>m1.xlarge</string>
                              <string>c1.xlarge</string>
                              <string>t1.micro</string>
                              <string>standard.xsmall</string>
                           </enumValues>
                           <value><![CDATA[m1.small]]></value>
                           <defaultValue><![CDATA[m1.small]]></defaultValue>
                        </parameter>
                     </entry>
                     <entry>
                        <string><![CDATA[InterouteV2.security.groups]]></string>
                        <parameter class="com.sixsq.slipstream.persistence.ModuleParameter" name="InterouteV2.security.groups" description="Security Groups (comma separated list)" category="InterouteV2" mandatory="true" type="String" readonly="false" order_="0" isSet="false" order="0"/>
                     </entry>
                     <entry>
                        <string><![CDATA[hostname]]></string>
                        <parameter class="com.sixsq.slipstream.persistence.ModuleParameter" name="hostname" description="hostname/ip of the image" category="Output" mandatory="true" type="String" readonly="false" order_="0" isSet="false" order="0"/>
                     </entry>
                     <entry>
                        <string><![CDATA[myCloud.security.groups]]></string>
                        <parameter class="com.sixsq.slipstream.persistence.ModuleParameter" name="myCloud.security.groups" description="Security Groups (comma separated list)" category="myCloud" mandatory="true" type="String" readonly="false" order_="0" isSet="true" order="0">
                           <value><![CDATA[default]]></value>
                           <defaultValue><![CDATA[default]]></defaultValue>
                        </parameter>
                     </entry>
                     <entry>
                        <string><![CDATA[nuvlabox.ram]]></string>
                        <parameter class="com.sixsq.slipstream.persistence.ModuleParameter" name="nuvlabox.ram" description="ram" category="nuvlabox" mandatory="true" type="String" readonly="false" order_="0" isSet="true" order="0">
                           <value><![CDATA[1]]></value>
                           <defaultValue><![CDATA[1]]></defaultValue>
                        </parameter>
                     </entry>
                     <entry>
                        <string><![CDATA[ready]]></string>
                        <parameter class="com.sixsq.slipstream.persistence.ModuleParameter" name="ready" description="Server ready to recieve connections" category="Output" mandatory="false" type="String" readonly="false" order_="0" isSet="false" order="0"/>
                     </entry>
                  </parameters>
                  <authz owner="super" ownerGet="true" ownerPut="true" ownerPost="true" ownerDelete="true" ownerCreateChildren="true" groupGet="true" groupPut="true" groupPost="true" groupDelete="false" groupCreateChildren="false" publicGet="true" publicPut="false" publicPost="true" publicDelete="false" publicCreateChildren="false" inheritedGroupMembers="true">
                     <groupMembers class="java.util.ArrayList"/>
                  </authz>
                  <commit author="super">
                     <comment>Changed Network type to Private</comment>
                  </commit>
                  <targets class="org.hibernate.collection.internal.PersistentSet">
                     <target runInBackground="false" name="report"><![CDATA[#!/bin/sh -x
cp /var/log/apache2/access.log $SLIPSTREAM_REPORT_DIR
cp /var/log/apache2/error.log $SLIPSTREAM_REPORT_DIR]]></target>
                     <target runInBackground="false" name="execute"><![CDATA[#!/bin/sh -xe
apt-get update -y
apt-get install -y apache2

echo 'Hello from Apache deployed by SlipStream!' > /var/www/data.txt

service apache2 stop
port=$(ss-get port)
sed -i -e 's/^Listen.*$/Listen '$port'/' /etc/apache2/ports.conf
sed -i -e 's/^NameVirtualHost.*$/NameVirtualHost *:'$port'/' /etc/apache2/ports.conf
sed -i -e 's/^<VirtualHost.*$/<VirtualHost *:'$port'>/' /etc/apache2/sites-available/default
service apache2 start
ss-set ready true
url="http://$(ss-get hostname):$port"
ss-set url.service $url
ss-set ss:url.service $url]]></target>
                  </targets>
                  <packages class="org.hibernate.collection.internal.PersistentSet"/>
                  <prerecipe><![CDATA[]]></prerecipe>
                  <recipe><![CDATA[]]></recipe>
                  <cloudImageIdentifiers class="org.hibernate.collection.internal.PersistentSet"/>
               </image>
            </node>
         </entry>
         <entry>
            <string>testclient</string>
            <node deleted="false" name="testclient" multiplicity="2" cloudService="myCloud" imageUri="module/examples/tutorials/service-testing/client" creation="2014-07-04 02:21:07.980 CEST" network="Private">
               <parameters class="org.hibernate.collection.internal.PersistentMap">
                  <entry>
                     <string><![CDATA[webserver.ready]]></string>
                     <parameter class="com.sixsq.slipstream.persistence.NodeParameter" name="webserver.ready" description="" category="General" mandatory="false" type="String" readonly="false" order_="0" isMappedValue="true" order="0">
                        <value><![CDATA[apache:ready]]></value>
                     </parameter>
                  </entry>
                  <entry>
                     <string><![CDATA[webserver.port]]></string>
                     <parameter class="com.sixsq.slipstream.persistence.NodeParameter" name="webserver.port" description="" category="General" mandatory="false" type="String" readonly="false" order_="0" isMappedValue="true" order="0">
                        <value><![CDATA[apache:port]]></value>
                     </parameter>
                  </entry>
                  <entry>
                     <string><![CDATA[webserver.hostname]]></string>
                     <parameter class="com.sixsq.slipstream.persistence.NodeParameter" name="webserver.hostname" description="" category="General" mandatory="false" type="String" readonly="false" order_="0" isMappedValue="true" order="0">
                        <value><![CDATA[apache:hostname]]></value>
                     </parameter>
                  </entry>
               </parameters>
               <parameterMappings class="org.hibernate.collection.internal.PersistentMap">
                  <entry>
                     <string>webserver.ready</string>
                     <nodeParameter name="webserver.ready" description="" category="General" mandatory="false" type="String" readonly="false" order_="0" isMappedValue="true" order="0">
                        <value><![CDATA[apache:ready]]></value>
                     </nodeParameter>
                  </entry>
                  <entry>
                     <string>webserver.port</string>
                     <nodeParameter name="webserver.port" description="" category="General" mandatory="false" type="String" readonly="false" order_="0" isMappedValue="true" order="0">
                        <value><![CDATA[apache:port]]></value>
                     </nodeParameter>
                  </entry>
                  <entry>
                     <string>webserver.hostname</string>
                     <nodeParameter name="webserver.hostname" description="" category="General" mandatory="false" type="String" readonly="false" order_="0" isMappedValue="true" order="0">
                        <value><![CDATA[apache:hostname]]></value>
                     </nodeParameter>
                  </entry>
               </parameterMappings>
               <image lastModified="2014-06-09 14:08:35.769 CEST" category="Image" description="Web client tests server connectivity and verifies content." deleted="false" resourceUri="module/examples/tutorials/service-testing/client/29" parentUri="module/examples/tutorials/service-testing" name="examples/tutorials/service-testing/client" version="29" isLatestVersion="true" moduleReferenceUri="module/examples/images/ubuntu-12.04" logoLink="" isBase="false" imageId="71651c3f-92de-4b75-b5f4-0bcfbf3b61c2" creation="2014-05-21 10:44:21.971 CEST" shortName="client" loginUser="" platform="ubuntu">
                  <parameters class="org.hibernate.collection.internal.PersistentMap">
                     <entry>
                        <string><![CDATA[instanceid]]></string>
                        <parameter class="com.sixsq.slipstream.persistence.ModuleParameter" name="instanceid" description="Cloud instance id" category="Output" mandatory="true" type="String" readonly="false" order_="0" isSet="false" order="0"/>
                     </entry>
                     <entry>
                        <string><![CDATA[nuvlabox.disks.bus.type]]></string>
                        <parameter class="com.sixsq.slipstream.persistence.ModuleParameter" name="nuvlabox.disks.bus.type" description="VM disks bus type" category="nuvlabox" mandatory="true" type="Enum" readonly="false" order_="0" isSet="true" order="0">
                           <enumValues length="2">
                              <string>virtio</string>
                              <string>scsi</string>
                           </enumValues>
                           <value><![CDATA[virtio]]></value>
                           <defaultValue><![CDATA[virtio]]></defaultValue>
                        </parameter>
                     </entry>
                     <entry>
                        <string><![CDATA[extra.disk.volatile]]></string>
                        <parameter class="com.sixsq.slipstream.persistence.ModuleParameter" name="extra.disk.volatile" description="Volatile extra disk in GB" category="Cloud" mandatory="true" type="String" readonly="false" order_="0" isSet="false" order="0"/>
                     </entry>
                     <entry>
                        <string><![CDATA[myCloud.instance.type]]></string>
                        <parameter class="com.sixsq.slipstream.persistence.ModuleParameter" name="myCloud.instance.type" description="Instance type (flavor)" category="myCloud" mandatory="true" type="String" readonly="false" order_="0" isSet="true" order="0">
                           <value><![CDATA[m1.tiny]]></value>
                           <defaultValue><![CDATA[m1.tiny]]></defaultValue>
                        </parameter>
                     </entry>
                     <entry>
                        <string><![CDATA[InterouteV2.networks]]></string>
                        <parameter class="com.sixsq.slipstream.persistence.ModuleParameter" name="InterouteV2.networks" description="List of networks (comma separated)" category="InterouteV2" mandatory="true" type="String" readonly="false" order_="0" isSet="true" order="0">
                           <value><![CDATA[HnxJgPrvWithGwServiceParis]]></value>
                           <defaultValue><![CDATA[HnxJgPrvWithGwServiceParis]]></defaultValue>
                        </parameter>
                     </entry>
                     <entry>
                        <string><![CDATA[webserver.ready]]></string>
                        <parameter class="com.sixsq.slipstream.persistence.ModuleParameter" name="webserver.ready" description="Server ready to recieve connections" category="Input" mandatory="false" type="String" readonly="false" order_="0" isSet="false" order="0"/>
                     </entry>
                     <entry>
                        <string><![CDATA[nuvlabox.cpu]]></string>
                        <parameter class="com.sixsq.slipstream.persistence.ModuleParameter" name="nuvlabox.cpu" description="cpu" category="nuvlabox" mandatory="true" type="String" readonly="false" order_="0" isSet="true" order="0">
                           <value><![CDATA[1]]></value>
                           <defaultValue><![CDATA[1]]></defaultValue>
                        </parameter>
                     </entry>
                     <entry>
                        <string><![CDATA[network]]></string>
                        <parameter class="com.sixsq.slipstream.persistence.ModuleParameter" name="network" description="Network type" category="Cloud" mandatory="true" type="Enum" readonly="false" order_="0" isSet="true" order="0">
                           <enumValues length="2">
                              <string>Public</string>
                              <string>Private</string>
                           </enumValues>
                           <value><![CDATA[Private]]></value>
                           <defaultValue><![CDATA[Private]]></defaultValue>
                        </parameter>
                     </entry>
                     <entry>
                        <string><![CDATA[webserver.port]]></string>
                        <parameter class="com.sixsq.slipstream.persistence.ModuleParameter" name="webserver.port" description="Port on which the web server listens" category="Input" mandatory="false" type="String" readonly="false" order_="0" isSet="false" order="0"/>
                     </entry>
                     <entry>
                        <string><![CDATA[InterouteV2.instance.type]]></string>
                        <parameter class="com.sixsq.slipstream.persistence.ModuleParameter" name="InterouteV2.instance.type" description="Instance type (flavor)" category="InterouteV2" mandatory="true" type="String" readonly="false" order_="0" isSet="true" order="0">
                           <value><![CDATA[512-1]]></value>
                           <defaultValue><![CDATA[512-1]]></defaultValue>
                        </parameter>
                     </entry>
                     <entry>
                        <string><![CDATA[nuvlabox.instance.type]]></string>
                        <parameter class="com.sixsq.slipstream.persistence.ModuleParameter" name="nuvlabox.instance.type" description="Cloud instance type" category="nuvlabox" mandatory="true" type="Enum" readonly="false" order_="0" isSet="true" order="0">
                           <enumValues length="7">
                              <string>m1.small</string>
                              <string>c1.medium</string>
                              <string>m1.large</string>
                              <string>m1.xlarge</string>
                              <string>c1.xlarge</string>
                              <string>t1.micro</string>
                              <string>standard.xsmall</string>
                           </enumValues>
                           <value><![CDATA[m1.small]]></value>
                           <defaultValue><![CDATA[m1.small]]></defaultValue>
                        </parameter>
                     </entry>
                     <entry>
                        <string><![CDATA[InterouteV2.security.groups]]></string>
                        <parameter class="com.sixsq.slipstream.persistence.ModuleParameter" name="InterouteV2.security.groups" description="Security Groups (comma separated list)" category="InterouteV2" mandatory="true" type="String" readonly="false" order_="0" isSet="false" order="0"/>
                     </entry>
                     <entry>
                        <string><![CDATA[hostname]]></string>
                        <parameter class="com.sixsq.slipstream.persistence.ModuleParameter" name="hostname" description="hostname/ip of the image" category="Output" mandatory="true" type="String" readonly="false" order_="0" isSet="false" order="0"/>
                     </entry>
                     <entry>
                        <string><![CDATA[myCloud.security.groups]]></string>
                        <parameter class="com.sixsq.slipstream.persistence.ModuleParameter" name="myCloud.security.groups" description="Security Groups (comma separated list)" category="myCloud" mandatory="true" type="String" readonly="false" order_="0" isSet="true" order="0">
                           <value><![CDATA[default]]></value>
                           <defaultValue><![CDATA[default]]></defaultValue>
                        </parameter>
                     </entry>
                     <entry>
                        <string><![CDATA[nuvlabox.ram]]></string>
                        <parameter class="com.sixsq.slipstream.persistence.ModuleParameter" name="nuvlabox.ram" description="ram" category="nuvlabox" mandatory="true" type="String" readonly="false" order_="0" isSet="true" order="0">
                           <value><![CDATA[1]]></value>
                           <defaultValue><![CDATA[1]]></defaultValue>
                        </parameter>
                     </entry>
                     <entry>
                        <string><![CDATA[webserver.hostname]]></string>
                        <parameter class="com.sixsq.slipstream.persistence.ModuleParameter" name="webserver.hostname" description="Server hostname" category="Input" mandatory="false" type="String" readonly="false" order_="0" isSet="false" order="0"/>
                     </entry>
                  </parameters>
                  <authz owner="super" ownerGet="true" ownerPut="true" ownerPost="true" ownerDelete="true" ownerCreateChildren="true" groupGet="true" groupPut="true" groupPost="true" groupDelete="false" groupCreateChildren="false" publicGet="true" publicPut="false" publicPost="true" publicDelete="false" publicCreateChildren="false" inheritedGroupMembers="true">
                     <groupMembers class="java.util.ArrayList"/>
                  </authz>
                  <commit author="super">
                     <comment></comment>
                  </commit>
                  <targets class="org.hibernate.collection.internal.PersistentSet">
                     <target runInBackground="false" name="report"><![CDATA[#!/bin/sh -x
cp /tmp/data.txt $SLIPSTREAM_REPORT_DIR]]></target>
                     <target runInBackground="false" name="execute"><![CDATA[#!/bin/sh -xe
# Wait for the metadata to be resolved
web_server_ip=$(ss-get --timeout 360 webserver.hostname)
web_server_port=$(ss-get --timeout 360 webserver.port)
ss-get --timeout 360 webserver.ready

# Execute the test
ENDPOINT=http://${web_server_ip}:${web_server_port}/data.txt
wget -t 2 -O /tmp/data.txt ${ENDPOINT}
[ "$?" = "0" ] & ss-set statecustom "OK: $(cat /tmp/data.txt)" || ss-abort "Could not get the test file: ${ENDPOINT}"
]]></target>
                  </targets>
                  <packages class="org.hibernate.collection.internal.PersistentSet"/>
                  <prerecipe><![CDATA[]]></prerecipe>
                  <recipe><![CDATA[]]></recipe>
                  <cloudImageIdentifiers class="org.hibernate.collection.internal.PersistentSet"/>
               </image>
            </node>
         </entry>
      </nodes>
   </module>
   <cloudServiceNameList length="1">
      <string>myCloud</string>
   </cloudServiceNameList>
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
        self.context['nodename'] = 'apache'

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
        targets = DomExtractor.getDeploymentTargets(etree.fromstring(RUN_XML),  'apache')
        self.assertEquals(targets['execute'][0].startswith('#!/bin/sh -xe\napt-get update -y\n'), True)
        self.assertEquals(False, targets['execute'][1])

        targets = DomExtractor.getDeploymentTargets(etree.fromstring(RUN_XML), 'testclient')
        self.assertEquals(targets['execute'][0].startswith('#!/bin/sh -xe\n# Wait for the metadata to be resolved\n'),
                          True)
        self.assertEquals(False, targets['execute'][1])

        for image_dom in etree.fromstring(RUN_XML).findall('module/nodes/entry/node/image'):
            targets = DomExtractor.getDeploymentTargetsFromImageDom(image_dom)
            if image_dom.attrib['name'] == 'test/apache':
                self.assertEquals('echo hello execute 1', targets['execute'][0])
                self.assertEquals(True, targets['execute'][1])
            elif image_dom.attrib['name'] == 'test/testclient':
                self.assertEquals('echo hello execute 2', targets['execute'][0])
                self.assertEquals(True, targets['execute'][1])

# Npt implemented in SlipStreamHttpClient because not needed
#    def test_extractNodesFromDeployment(self):
#        nodes = DomExtractor.extract_nodes_instances_runtime_parameters(etree.fromstring(RUN_XML), 'myCloud')
#        self.assertEquals(4, len(nodes))
#        for node in nodes:
#            assert isinstance(node['image'], ElementTree._Element)
#            if node['nodename'] == 'apache':
#                self.assertEquals(1, node['multiplicity'])
#                self.assertEquals('foo', node['cloudService'])
#            elif node['nodename'] == 'testclient':
#                self.assertEquals(2, node['multiplicity'])
#                self.assertEquals('bar', node['cloudService'])

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
        targets = DomExtractor.get_build_targets(dom)

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
            if node_dom.get('name') == 'apache':
                assert extra_disks == {}
            elif node_dom.get('name') == 'testclient':
                assert extra_disks['extra.disk.volatile'] == 'foo'

    def test_getUserInfoUser(self):
        client = SlipStreamHttpClient(ConfigHolder(config={'foo': 'bar'},
                                                   context=self.context))
        client._getUserContent = Mock(return_value=USERPARAMETRS_XML)
        userInfo = client.get_user_info('')
        assert 'Test' == userInfo.get_user('firstName')
        assert 'User' == userInfo.get_user('lastName')
        assert 'test@sixsq.com' == userInfo.get_user('email')

    def test_getUserInfo(self):
        client = SlipStreamHttpClient(ConfigHolder(config={'foo': 'bar'},
                                                   context=self.context))
        client._getUserContent = Mock(return_value=USERPARAMETRS_XML)
        userInfo = client.get_user_info('StratusLab')

        assert 'test@sixsq.com' == userInfo.get_user('email')

        assert 'cloud.lal.stratuslab.eu' == userInfo.get_cloud('endpoint')
        assert 'public' == userInfo.get_cloud('ip.type')
        assert 'ssh-rsa abc' == userInfo.get_general('ssh.public.key')

        assert 'on' == userInfo.get_general('On Error Run Forever')
        assert '3' == userInfo.get_general('Verbosity Level')

    def test_cloud_params_and_network(self):
        client = SlipStreamHttpClient(ConfigHolder(context=self.context,
                                                   config={'foo': 'bar'}))
        client._httpGet = Mock(return_value=(200, RUN_XML))

        nodes = client.get_nodes_instances()

        assert nodes['apache.1'].get('myCloud.cpu') is None
        assert nodes['apache.1']['myCloud.instance.type'] == 'm1.tiny'
        assert nodes['apache.1']['myCloud.security.groups'] == 'default'
        assert nodes['apache.1']['network'] == 'Private'

    def test_get_nodes_instances(self):
        client = SlipStreamHttpClient(ConfigHolder(context=self.context,
                                                   config={'foo': 'bar'}))
        client._httpGet = Mock(return_value=(200, RUN_XML))

        nodes_instances = client.get_nodes_instances()
        assert len(nodes_instances) == 4

        node_keys = ['cloudservice', 'nodename', 'name', 'id']
        for nodes_instance in nodes_instances:
            for key in node_keys:
                if nodes_instances[nodes_instance]['is.orchestrator'] == 'false':
                    self.assertTrue(key in nodes_instances[nodes_instance], 'No element %s' % key)

if __name__ == '__main__':
    unittest.main()

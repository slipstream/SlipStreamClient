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

import unittest

from slipstream.exceptions.Exceptions import ValidationException as ValidationException
import slipstream.commands.NodeInstanceRuntimeParameter as NodeInstanceRuntimeParameter

class TestCloudConnectorsBase(unittest.TestCase):

    def test_valide_runtime_parameter_value(self):
        NodeInstanceRuntimeParameter.validate('rp_name:value')
        NodeInstanceRuntimeParameter.validate('rp_name:value1,value2')
    
    def test_invalide_runtime_parameter_value(self):
        self.assertRaises(ValidationException, NodeInstanceRuntimeParameter.validate, '')
        self.assertRaises(ValidationException, NodeInstanceRuntimeParameter.validate, ':')
        self.assertRaises(ValidationException, NodeInstanceRuntimeParameter.validate, 'rp_name:')
        self.assertRaises(ValidationException, NodeInstanceRuntimeParameter.validate, ':value1,value2')
        self.assertRaises(ValidationException, NodeInstanceRuntimeParameter.validate, ':,')
    
    def test_parse_runtime_parameter(self):
        name,values = NodeInstanceRuntimeParameter.parse_option_value('rp_name:value1,value2')
        self.assertEqual(name, 'rp_name')
        self.assertEqual(len(values), 2)
        self.assertListEqual(values, ['value1','value2'])

    def test_parse_added_node_instances(self):
        ids = NodeInstanceRuntimeParameter.parse_added_node_instances('node1.3')
        self.assertEqual([3], ids)
        ids = NodeInstanceRuntimeParameter.parse_added_node_instances('node1.3,node1.4,node1.5,node1.6')
        self.assertEqual([3,4,5,6], ids)
        
    def test_generate_mapping_index_name_value(self):
        nodeName = 'nname'
        paramName = 'pname'
        values = ['aa','bb']
        ids = [10,11,12]
        mapped = NodeInstanceRuntimeParameter.generate_mapping_index_name_value(nodeName, paramName, values, ids)
        self.assertEqual({'nname.10:pname':'aa','nname.11:pname':'bb'}, mapped)
        
        
        
        
        
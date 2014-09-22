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

from slipstream.exceptions.Exceptions import ValidationException as ValidationException

name_value_separator = ':'
values_separator = ','

def validate(rp):
    _validate(rp, _name_value_validator)
    _,value = _split_name_value(rp)
    _validate(value, _values_validator)
    
def _validate(value, validator_func):
    validator_func(value)

def _name_value_validator(value):

    targetString = 'runtime parameter'
    separator = name_value_separator

    if not value:
        raise ValidationException('Empty %s' % targetString)
    if separator not in value:
        raise ValidationException('Invalid %s, missing "%s" separator' % (targetString, separator))

    name,values = _split_name_value(value)
    if name == '':
        raise ValidationException('Invalid %s, missing name' % targetString)
    if values == '':
        raise ValidationException('Invalid %s, missing value' % targetString)

def _split_name_value(value):
    name,values = value.split(name_value_separator)
    return name,values
    
def _split_values(values):
    return values.split(values_separator)
    
def _values_validator(values):

    targetString = 'runtime parameter value'

    if not values:
        raise ValidationException('Empty %s' % targetString)

    values = _split_values(values)
    if not values:
        raise ValidationException('Invalid %s, missing values' % targetString)
    
def parse_option_value(rp):
    name,values = _split_name_value(rp)
    values = _split_values(values)
    return name, values
    
def parse_added_node_instances(instances):
    return [int(n.split('.')[-1]) for n in instances.split(',')]

def generate_mapping_index_name_value(nodeName, paramName, values, ids):
    qualified = [nodeName + '.' + str(i) + ':' + paramName for i in ids]
    return dict(zip(qualified,values))



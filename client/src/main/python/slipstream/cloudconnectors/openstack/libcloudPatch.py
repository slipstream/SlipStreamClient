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
import base64
from libcloud.utils.py3 import b
from libcloud.utils.py3 import httplib
from libcloud.compute.drivers.openstack import OpenStack_1_1_NodeDriver


class OpenStackSecurityGroup(object):

    """
    A Security Group.
    """

    def __init__(self, id, tenant_id, name, description, driver, rules=None,
                 extra=None):
        self.id = id
        self.tenant_id = tenant_id
        self.name = name
        self.description = description
        self.driver = driver
        self.rules = rules or []
        self.extra = extra or {}

    def __repr__(self):
        return '<OpenStackSecurityGroup id="%s" tenant_id="%s" name="%s" \
        description="%s">' % (self.id, self.tenant_id, self.name,
                              self.description)


class OpenStackSecurityGroupRule(object):

    """
    A Rule of a Security Group.
    """

    def __init__(self, id, parent_group_id, ip_protocol, from_port, to_port,
                 driver, ip_range=None, group=None, tenant_id=None,
                 extra=None):
        self.id = id
        self.parent_group_id = parent_group_id
        self.ip_protocol = ip_protocol
        self.from_port = from_port
        self.to_port = to_port
        self.driver = driver
        self.ip_range = ''
        self.group = {}
        if group is None:
            self.ip_range = ip_range
        else:
            self.group = {'name': group, 'tenant_id': tenant_id}
        self.extra = extra or {}

    def __repr__(self):
        return '<OpenStackSecurityGroupRule id="%s" parent_group_id="%s" \
        ip_protocol="%s" from_port="%s" to_port="%s">' % (self.id,
                                                          self.parent_group_id, self.ip_protocol, self.from_port,
                                                          self.to_port)


class OpenStackKeyPair(object):

    """
    A KeyPair.
    """

    def __init__(self, name, fingerprint, public_key, driver, private_key=None,
                 extra=None):
        """
        Constructor.

        @keyword    name: Name of the KeyPair.
        @type       name: C{str}

        @keyword    fingerprint: Fingerprint of the KeyPair
        @type       fingerprint: C{str}

        @keyword    public_key: Public key in OpenSSH format.
        @type       public_key: C{str}

        @keyword    private_key: Private key in PEM format.
        @type       private_key: C{str}

        @keyword    extra: Extra attributes associated with this KeyPair.
        @type       extra: C{dict}
        """
        self.name = name
        self.fingerprint = fingerprint
        self.public_key = public_key
        self.private_key = private_key
        self.driver = driver
        self.extra = extra or {}

    def __repr__(self):
        return ('<OpenStackKeyPair name=%s fingerprint=%s public_key=%s ...>'
                % (self.name, self.fingerprint, self.public_key))


def create_node(self, **kwargs):
    """Create a new node

    @inherits:  L{NodeDriver.create_node}

    @keyword    ex_metadata: Key/Value metadata to associate with a node
    @type       ex_metadata: C{dict}

    @keyword    ex_files:   File Path => File contents to create on
                            the no  de
    @type       ex_files:   C{dict}

    @keyword    ex_keyname:  Name of existing public key to inject into
                             instance
    @type       ex_keyname:  C{str}

    @keyword    ex_userdata: String containing user data
                             see
                             https://help.ubuntu.com/community/CloudInit
    @type       ex_userdata: C{str}

    @keyword    networks: The server is launched into a set of Networks.
    @type       networks: L{OpenStackNetwork}

    @keyword    ex_security_groups: List of security groups to assign to
                                    the node
    @type       ex_security_groups: C{list} of L{OpenStackSecurityGroup} or
                                    C{list} of C{str}
    """

    server_params = self._create_args_to_params(None, **kwargs)

    resp = self.connection.request("/servers",
                                   method='POST',
                                   data={'server': server_params})

    create_response = resp.object['server']
    server_resp = self.connection.request(
        '/servers/%s' % create_response['id'])
    server_object = server_resp.object['server']
    server_object['adminPass'] = create_response['adminPass']

    return self._to_node(server_object)


def _create_args_to_params(self, node, **kwargs):
    server_params = {
        'name': kwargs.get('name'),
        'metadata': kwargs.get('ex_metadata', {}),
        'personality': self._files_to_personality(kwargs.get("ex_files", {}))
    }

    if 'ex_keyname' in kwargs:
        server_params['key_name'] = kwargs['ex_keyname']

    if 'ex_userdata' in kwargs:
        server_params['user_data'] = base64.b64encode(
            b(kwargs['ex_userdata'])).decode('ascii')

    if 'networks' in kwargs:
        networks = kwargs['networks']
        networks = [{'uuid': network.id} for network in networks]
        server_params['networks'] = networks

    if 'ex_security_groups' in kwargs:
        server_params['security_groups'] = list()
        for security_group in kwargs['ex_security_groups']:
            name = str()
            if type(security_group) == OpenStackSecurityGroup:
                name = security_group.name
            else:
                name = security_group
            server_params['security_groups'].append({'name': name})

    if 'name' in kwargs:
        server_params['name'] = kwargs.get('name')
    else:
        server_params['name'] = node.name

    if 'image' in kwargs:
        server_params['imageRef'] = kwargs.get('image').id
    else:
        server_params['imageRef'] = node.extra.get('imageId')

    if 'size' in kwargs:
        server_params['flavorRef'] = kwargs.get('size').id
    else:
        server_params['flavorRef'] = node.extra.get('flavorId')

    return server_params


def _to_security_group_rules(self, obj):
    return [self._to_security_group_rule(security_group_rule) for
            security_group_rule in obj]


def _to_security_group_rule(self, obj):
    ip_range = group = tenant_id = None
    if obj['group'] == {}:
        ip_range = obj['ip_range'].get('cidr', None)
    else:
        group = obj['group'].get('name', None)
        tenant_id = obj['group'].get('tenant_id', None)
    return OpenStackSecurityGroupRule(id=obj['id'],
                                      parent_group_id=
                                      obj['parent_group_id'],
                                      ip_protocol=obj['ip_protocol'],
                                      from_port=obj['from_port'],
                                      to_port=obj['to_port'],
                                      driver=self,
                                      ip_range=ip_range,
                                      group=group,
                                      tenant_id=tenant_id)


def _to_security_groups(self, obj):
    security_groups = obj['security_groups']
    return [self._to_security_group(security_group) for security_group in
            security_groups]


def _to_security_group(self, obj):
    return OpenStackSecurityGroup(id=obj['id'],
                                  tenant_id=obj['tenant_id'],
                                  name=obj['name'],
                                  description=obj.get('description', ''),
                                  rules=self._to_security_group_rules(
                                      obj.get('rules', [])),
                                  driver=self)


def ex_list_security_groups(self):
    """
    Get a list of Security Groups that are available.

    @rtype: C{list} of L{OpenStackSecurityGroup}
    """
    return self._to_security_groups(
        self.connection.request('/os-security-groups').object)


def ex_get_node_security_groups(self, node):
    """
    Get Security Groups of the specified server.

    @rtype: C{list} of L{OpenStackSecurityGroup}
    """
    return self._to_security_groups(
        self.connection.request('/servers/%s/os-security-groups' % node.id).object)


def ex_create_security_group(self, name, description):
    """
    Create a new Security Group

    @param name: Name of the new Security Group
    @type  name: C{str}

    @param description: Description of the new Security Group
    @type  description: C{str}

    @param rules: List of rules to add to this security group
    @type  rules: C{list} of L{OpenStackSecurityGroupRule}

    @rtype: L{OpenStackSecurityGroup}
    """
    return self._to_security_group(self.connection.request(
        '/os-security-groups', method='POST',
        data={'security_group': {'name': name, 'description': description}}
    ).object['security_group'])


def ex_delete_security_group(self, security_group):
    """
    Delete a Security Group.

    @param security_group: Security Group should be deleted
    @type  security_group: L{OpenStackSecurityGroup}

    @rtype: C{bool}
    """
    resp = self.connection.request(
        '/os-security-groups/%s' % security_group.id,
        method='DELETE')
    return resp.status == httplib.NO_CONTENT


def ex_create_security_group_rule(self, security_group, ip_protocol,
                                  from_port, to_port, cidr=None,
                                  source_security_group=None):
    """
    Create a new Rule in a Security Group

    @param security_group: Security Group in which to add the rule
    @type  security_group: L{OpenStackSecurityGroup}

    @param ip_protocol: Protocol to which this rule applies
                        Examples: tcp, udp, ...
    @type  ip_protocol: C{str}

    @param from_port: First port of the port range
    @type  from_port: C{int}

    @param to_port: Last port of the port range
    @type  to_port: C{int}

    @param cidr: CIDR notation of the source IP range for this rule
    @type  cidr: C{str}

    @param source_security_group: Existing Security Group to use as the
                                  source (instead of CIDR)
    @type  source_security_group: L{OpenStackSecurityGroup

    @rtype: L{OpenStackSecurityGroupRule}
    """
    source_security_group_id = None
    if type(source_security_group) == OpenStackSecurityGroup:
        source_security_group_id = source_security_group.id

    return self._to_security_group_rule(self.connection.request(
        '/os-security-group-rules', method='POST',
        data={'security_group_rule': {
            'ip_protocol': ip_protocol,
            'from_port': from_port,
            'to_port': to_port,
            'cidr': cidr,
            'group_id': source_security_group_id,
            'parent_group_id': security_group.id}}
    ).object['security_group_rule'])


def ex_delete_security_group_rule(self, rule):
    """
    Delete a Rule from a Security Group.

    @param rule: Rule should be deleted
    @type  rule: L{OpenStackSecurityGroupRule}

    @rtype: C{bool}
    """
    resp = self.connection.request('/os-security-group-rules/%s' % rule.id,
                                   method='DELETE')
    return resp.status == httplib.NO_CONTENT


def _to_keypairs(self, obj):
    keypairs = obj['keypairs']
    return [self._to_keypair(keypair['keypair']) for keypair in keypairs]


def _to_keypair(self, obj):
    return OpenStackKeyPair(name=obj['name'],
                            fingerprint=obj['fingerprint'],
                            public_key=obj['public_key'],
                            private_key=obj.get('private_key', None),
                            driver=self)


def ex_list_keypairs(self):
    """
    Get a list of KeyPairs that are available.

    @rtype: C{list} of L{OpenStackKeyPair}
    """
    return self._to_keypairs(
        self.connection.request('/os-keypairs').object)


def ex_create_keypair(self, name):
    """
    Create a new KeyPair

    @param name: Name of the new KeyPair
    @type  name: C{str}

    @rtype: L{OpenStackKeyPair}
    """
    return self._to_keypair(self.connection.request(
        '/os-keypairs', method='POST',
        data={'keypair': {'name': name}}
    ).object['keypair'])


def ex_import_keypair(self, name, public_key_file):
    """
    Import a KeyPair from a file

    @param name: Name of the new KeyPair
    @type  name: C{str}

    @param public_key_file: Path to the public key file (in OpenSSH format)
    @type  public_key_file: C{str}

    @rtype: L{OpenStackKeyPair}
    """
    public_key = open(os.path.expanduser(public_key_file), 'r').read()
    return self.ex_import_keypair_from_string(name, public_key)


def ex_import_keypair_from_string(self, name, public_key):
    """
    Import a KeyPair from a string

    @param name: Name of the new KeyPair
    @type  name: C{str}

    @param public_key: Public key (in OpenSSH format)
    @type  public_key: C{str}

    @rtype: L{OpenStackKeyPair}
    """
    return self._to_keypair(self.connection.request(
        '/os-keypairs', method='POST',
        data={'keypair': {'name': name, 'public_key': public_key}}
    ).object['keypair'])


def ex_delete_keypair(self, keypair):
    """
    Delete a KeyPair.

    @param keypair: KeyPair to delete
    @type  keypair: L{OpenStackKeyPair}

    @rtype: C{bool}
    """
    resp = self.connection.request('/os-keypairs/%s' % keypair.name,
                                   method='DELETE')
    return resp.status == httplib.ACCEPTED


def patchLibcloud():
    OpenStack_1_1_NodeDriver.create_node = create_node
    OpenStack_1_1_NodeDriver._create_args_to_params = _create_args_to_params
    OpenStack_1_1_NodeDriver._to_security_group_rules = _to_security_group_rules
    OpenStack_1_1_NodeDriver._to_security_group_rule = _to_security_group_rule
    OpenStack_1_1_NodeDriver._to_security_groups = _to_security_groups
    OpenStack_1_1_NodeDriver._to_security_group = _to_security_group
    OpenStack_1_1_NodeDriver.ex_list_security_groups = ex_list_security_groups
    OpenStack_1_1_NodeDriver.ex_get_node_security_groups = ex_get_node_security_groups
    OpenStack_1_1_NodeDriver.ex_create_security_group = ex_create_security_group
    OpenStack_1_1_NodeDriver.ex_delete_security_group = ex_delete_security_group
    OpenStack_1_1_NodeDriver.ex_create_security_group_rule = ex_create_security_group_rule
    OpenStack_1_1_NodeDriver.ex_delete_security_group_rule = ex_delete_security_group_rule
    OpenStack_1_1_NodeDriver._to_keypairs = _to_keypairs
    OpenStack_1_1_NodeDriver._to_keypair = _to_keypair
    OpenStack_1_1_NodeDriver.ex_list_keypairs = ex_list_keypairs
    OpenStack_1_1_NodeDriver.ex_create_keypair = ex_create_keypair
    OpenStack_1_1_NodeDriver.ex_import_keypair = ex_import_keypair
    OpenStack_1_1_NodeDriver.ex_import_keypair_from_string = ex_import_keypair_from_string
    OpenStack_1_1_NodeDriver.ex_delete_keypair = ex_delete_keypair

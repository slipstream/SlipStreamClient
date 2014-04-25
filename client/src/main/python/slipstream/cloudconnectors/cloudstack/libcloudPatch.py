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

# In the waiting of libcloud 0.13.3 this patch correspond to these commits:
# - https://github.com/apache/libcloud/commit/f798a248604c4ca08bbb658b71e7a9cfceedf56e
# - https://github.com/apache/libcloud/commit/2be6b006928639917cbda1641a98eeb5a13040a3
# - https://github.com/apache/libcloud/commit/f15bc5ed2ecef63db51dbebdbc8654e09e296483

import os
import base64
from libcloud.utils.py3 import b
from libcloud.compute.base import is_private_subnet
from libcloud.compute.types import LibcloudError
from libcloud.compute.drivers.cloudstack import CloudStackNodeDriver, CloudStackNode


def create_node(self, **kwargs):
    """
    Create a new node

    @inherits: :class:`NodeDriver.create_node`

    :keyword ex_keyname: Name of existing keypair
    :type ex_keyname: ``str``

    :keyword ex_userdata: String containing user data
    :type ex_userdata: ``str``

    :keyword networks: The server is launched into a set of Networks.
    :type networks: :class:`CloudStackNetwork`

    :keyword ex_security_groups: List of security groups to assign to
    the node
    :type ex_security_groups: ``list`` of ``str``

    :rtype: :class:`CloudStackNode`
    """

    server_params = self._create_args_to_params(None, **kwargs)

    node = self._async_request('deployVirtualMachine',
                               **server_params)['virtualmachine']
    public_ips = []
    private_ips = []
    for nic in node['nic']:
        if is_private_subnet(nic['ipaddress']):
            private_ips.append(nic['ipaddress'])
        else:
            public_ips.append(nic['ipaddress'])

    keypair, password, securitygroup = None, None, None
    if 'keypair' in node.keys():
        keypair = node['keypair']
    if 'password' in node.keys():
        password = node['password']
    if 'securitygroup' in node.keys():
        securitygroup = [sg['name'] for sg in node['securitygroup']]

    return CloudStackNode(
        id=node['id'],
        name=node['displayname'],
        state=self.NODE_STATE_MAP[node['state']],
        public_ips=public_ips,
        private_ips=private_ips,
        driver=self,
        extra={'zoneid': server_params['zoneid'],
               'ip_addresses': [],
               'ip_forwarding_rules': [],
               'port_forwarding_rules': [],
               'password': password,
               'keyname': keypair,
               'securitygroup': securitygroup,
               'created': node['created']
               }

    )


def _create_args_to_params(self, node, **kwargs):
    server_params = {
        'name': kwargs.get('name'),
    }

    if 'name' in kwargs:
        server_params['displayname'] = kwargs.get('name')

    if 'size' in kwargs:
        server_params['serviceofferingid'] = kwargs.get('size').id

    if 'image' in kwargs:
        server_params['templateid'] = kwargs.get('image').id

    if 'location' in kwargs:
        server_params['zoneid'] = kwargs.get('location').id
    else:
        server_params['zoneid'] = self.list_locations()[0].id

    if 'ex_keyname' in kwargs:
        server_params['keypair'] = kwargs['ex_keyname']

    if 'ex_userdata' in kwargs:
        server_params['userdata'] = base64.b64encode(
            b(kwargs['ex_userdata'])).decode('ascii')

    if 'networks' in kwargs:
        networks = kwargs['networks']
        networks = ','.join([network.id for network in networks])
        server_params['networkids'] = networks

    if 'ex_security_groups' in kwargs:
        security_groups = kwargs['ex_security_groups']
        security_groups = ','.join(security_groups)
        server_params['securitygroupnames'] = security_groups

    return server_params


def ex_list_keypairs(self, **kwargs):
    """
    List Registered SSH Key Pairs

    @param projectid: list objects by project
    @type projectid: C{uuid}

    @param page: The page to list the keypairs from
    @type page: C{int}

    @param keyword: List by keyword
    @type keyword: C{str}

    @param listall: If set to false, list only resources
    belonging to the command's caller;
    if set to true - list resources that
    the caller is authorized to see.
    Default value is false

    @type listall: C{bool}

    @param pagesize: The number of results per page
    @type pagesize: C{int}

    @param account: List resources by account.
    Must be used with the domainId parameter
    @type account: C{str}

    @param isrecursive: Defaults to false, but if true,
    lists all resources from
    the parent specified by the
    domainId till leaves.
    @type isrecursive: C{bool}

    @param fingerprint: A public key fingerprint to look for
    @type fingerprint: C{str}

    @param name: A key pair name to look for
    @type name: C{str}

    @param domainid: List only resources belonging to
    the domain specified
    @type domainid: C{uuid}

    @return: A list of keypair dictionaries
    @rtype: L{dict}
    """

    extra_args = {}
    for key in kwargs.keys():
        extra_args[key] = kwargs[key]

    res = self._sync_request('listSSHKeyPairs', **extra_args)
    return res['sshkeypair']


def ex_create_keypair(self, name, **kwargs):
    """
    Creates a SSH KeyPair, returns fingerprint and private key

    @param name: Name of the keypair (required)
    @type name: C{str}

    @param projectid: An optional project for the ssh key
    @type projectid: C{str}

    @param domainid: An optional domainId for the ssh key.
    If the account parameter is used,
    domainId must also be used.
    @type domainid: C{str}

    @param account: An optional account for the ssh key.
    Must be used with domainId.
    @type account: C{str}

    @return: A keypair dictionary
    @rtype: C{dict}
    """

    extra_args = {}
    for key in kwargs.keys():
        extra_args[key] = kwargs[key]

    for keypair in self.ex_list_keypairs():
        if keypair['name'] == name:
            raise LibcloudError('SSH KeyPair with name=%s already exists'
                                % name)

    res = self._sync_request('createSSHKeyPair', name=name, **extra_args)
    return res['keypair']


def ex_delete_keypair(self, name, **kwargs):
    """
    Deletes an existing SSH KeyPair

    @param name: Name of the keypair (required)
    @type name: C{str}

    @param projectid: The project associated with keypair
    @type projectid: C{uuid}

    @param domainid : The domain ID associated with the keypair
    @type domainid: C{uuid}

    @param account : The account associated with the keypair.
    Must be used with the domainId parameter.
    @type account: C{str}

    @return: True of False based on success of Keypair deletion
    @rtype: C{bool}
    """

    extra_args = {}
    for key in kwargs.keys():
        extra_args[key] = kwargs[key]

    res = self._sync_request('deleteSSHKeyPair', name=name, **extra_args)
    return res['success']


def ex_import_keypair_from_string(self, name, key_material):
    """
    Imports a new public key where the public key is passed in as a string

    @param name: The name of the public key to import.
    @type name: C{str}

    @param key_material: The contents of a public key file.
    @type key_material: C{str}

    @rtype: C{dict}
    """

    res = self._sync_request('registerSSHKeyPair', name=name,
                             publickey=key_material)
    return {
        'keyName': res['keypair']['name'],
        'keyFingerprint': res['keypair']['fingerprint']
    }


def ex_import_keypair(self, name, keyfile):
    """
    Imports a new public key where the public key is passed via a filename

    @param name: The name of the public key to import.
    @type name: C{str}

    @param keyfile: The filename with path of the public key to import.
    @type keyfile: C{str}

    @rtype: C{dict}
    """
    with open(os.path.expanduser(keyfile)) as fh:
        content = fh.read()
    return self.ex_import_keypair_from_string(name, content)


def patchLibcloud():
    CloudStackNodeDriver.create_node = create_node
    CloudStackNodeDriver._create_args_to_params = _create_args_to_params
    CloudStackNodeDriver.ex_list_keypairs = ex_list_keypairs
    CloudStackNodeDriver.ex_create_keypair = ex_create_keypair
    CloudStackNodeDriver.ex_delete_keypair = ex_delete_keypair
    CloudStackNodeDriver.ex_import_keypair_from_string = ex_import_keypair_from_string
    CloudStackNodeDriver.ex_import_keypair = ex_import_keypair

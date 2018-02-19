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


class UserInfo(dict):

    SEPARATOR = '.'
    CLOUD_USERNAME_KEY = 'key'
    CLOUD_PASSWORD_KEY = 'secret'

    def __init__(self, cloud_qualifier):
        super(UserInfo, self).__init__({})
        self.cloud = cloud_qualifier + self.SEPARATOR
        self.user = 'User' + self.SEPARATOR
        self.general = 'General' + self.SEPARATOR
        self.qualifires = (self.cloud, self.user, self.general)

    def get_cloud(self, key, default_value=None):
        return self.get(self.cloud + key, default_value)

    def get_general(self, key, default_value=None):
        return self.get(self.general + key, default_value)

    def get_user(self, key, default_value=None):
        return self.get(self.user + key, default_value)

    def __setitem__(self, key, val):
        if not key.startswith(self.qualifires):
            raise ValueError('Invalid key: %s. Key should start with one of: %s' %
                             (key, ', '.join(self.qualifires)))
        dict.__setitem__(self, key, val)

    def get_first_name(self):
        return self.get_user('firstName')

    def get_last_name(self):
        return self.get_user('lastName')

    def get_email(self):
        return self.get_user('emailAddress')

    def get_cloud_username(self):
        return self.get_cloud(self.CLOUD_USERNAME_KEY)

    def get_cloud_password(self):
        return self.get_cloud(self.CLOUD_PASSWORD_KEY)

    def get_cloud_endpoint(self):
        return self.get_cloud('endpoint')

    def get_public_keys(self):
        return self.get_general('sshPublicKey')

    def get_private_key(self):
        return self.get_cloud('private.key')

    def get_keypair_name(self):
        return self.get_cloud('keypair.name')

    def get_public_network_name(self):
        return self.get_cloud('networkPublic', '').strip()

    def get_private_network_name(self):
        return self.get_cloud('networkPrivate', '').strip()

    def set_private_key(self, private_key):
        self[self.cloud + 'private.key'] = private_key

    def set_keypair_name(self, keypair_name):
        self[self.cloud + 'keypair.name'] = keypair_name

    def set_cloud_params(self, params):
        for k,v in params.iteritems():
            self[self.cloud + k] = v

    def set_general_params(self, params):
        for k,v in params.iteritems():
            self[self.general + k] = v

    def set_user_params(self, params):
        for k,v in params.iteritems():
            self[self.user + k] = v

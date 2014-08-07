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
    def __init__(self, cloud_qualifier):
        super(UserInfo, self).__init__({})
        self.cloud = cloud_qualifier + '.'
        self.user = 'User.'
        self.general = 'General.'
        self.qualifires = (self.cloud, self.user, self.general)

    def get_cloud(self, key):
        return self.__getitem__(self.cloud + key)

    def get_general(self, key):
        return self.__getitem__(self.general + key)

    def get_user(self, key):
        return self.__getitem__(self.user + key)

    def __setitem__(self, key, val):
        if not key.startswith(self.qualifires):
            raise ValueError('Key should start with one of: %s' %
                ', '.join(self.qualifires))
        dict.__setitem__(self, key, val)

    def get_first_name(self):
        return self.get_user('firstName')

    def get_last_name(self):
        return self.get_user('lastName')

    def get_email(self):
        return self.get_user('email')

    def get_cloud_username(self):
        return self.get_cloud('username')

    def get_cloud_password(self):
        return self.get_cloud('password')

    def get_cloud_endpoint(self):
        return self.get_cloud('endpoint')

    def get_public_keys(self):
        return self.get_general('ssh.public.key')

    def get_private_key(self):
        return self.get_cloud('private.key')

    def get_keypair_name(self):
        return self.get_cloud('keypair.name')

    def set_private_key(self, private_key):
        self[self.cloud + 'private.key'] = private_key

    def set_keypair_name(self, keypair_name):
        self[self.cloud + 'keypair.name'] = keypair_name

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

import struct
import binascii
from Crypto.PublicKey.RSA import _RSAobj
from Crypto.Util.number import long_to_bytes
from Crypto.Util.py3compat import bord, bchr


def exportSSHKey(self):
    eb = long_to_bytes(self.e)
    nb = long_to_bytes(self.n)
    if bord(eb[0]) & 0x80: eb = bchr(0x00) + eb
    if bord(nb[0]) & 0x80: nb = bchr(0x00) + nb
    keyparts = ['ssh-rsa', eb, nb]
    keystring = ''.join([struct.pack(">I", len(kp)) + kp for kp in keyparts])
    return 'ssh-rsa ' + binascii.b2a_base64(keystring)[:-1]


def pyCryptoPatch():
    _RSAobj.exportSSHKey = exportSSHKey

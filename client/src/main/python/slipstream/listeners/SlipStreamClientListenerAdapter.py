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

from slipstream.listeners.SimplePrintListener import SimplePrintListener
from slipstream.NodeDecorator import NodeDecorator


class SlipStreamClientListenerAdapter(SimplePrintListener):
    def __init__(self, slipStremClient):
        super(SlipStreamClientListenerAdapter, self).__init__()
        self._client = slipStremClient
        self._parameter = NodeDecorator.NODE_PROPERTY_SEPARATOR + \
            NodeDecorator.STATECUSTOM_KEY
        self.write = self._write

    def _write(self, msg):
        self.write_for(self._client.nodename, msg)
        
    def write_for(self, nodename, msg):
        param = nodename + self._parameter
        self._client.setRuntimeParameter(param, msg)

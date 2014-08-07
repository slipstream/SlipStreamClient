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


class SimplePrintListener(object):
    def __init__(self, verbose=False):
        if verbose:
            self.write = self.__beVerbose

    def write(self, msg):
        pass

    def write_for(self, nodename, msg):
        self.write(nodename + ': ' + msg)

    def __beVerbose(self, msg):
        print msg

    def onAction(self, msg):
        self.write('action: %s' % msg)

    def onStep(self, msg):
        self.write('step: %s' % msg)

    def onError(self, msg):
        self.write('error: %s' % msg)

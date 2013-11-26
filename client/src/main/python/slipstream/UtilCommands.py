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
import shutil

import slipstream.exceptions.Exceptions as Exceptions


class ConfigFileReplacer:
    def __init__(self):
        self.pattern = None
        self.configFilename = None
        self.newConfigFilename = None
        self.newValue = None
        return

    def parseAndReplaceConfigFile(self, patternList, newvalue, configFilename):
        """patternList is a list of sections/options to locate the value to change
           to the newvalue. The format is: ([<section>],<key), where the section
           is optional."""

        self.pattern = patternList
        self.configFilename = configFilename
        self.newValue = newvalue

        gotit = self._parse()

        if gotit:
            self._replaceConfigFile()
        else:
            os.remove(self.newConfigFilename)
            raise Exceptions.NotFoundError("Couldn't find patternList %s in in config file %s" %
                                           (patternList, configFilename))
        return

    def _parse(self):
        newConfigFile = self._openNewConfigFile()
        gotit = False
        key = self._getFirstKey()
        for line in open(self.configFilename):
            if key in line:
                try:
                    key = self._getNextKey()
                except IndexError:
                    bits = line.split('=')
                    line = bits[0] + ' = ' + self.newValue + '\n'
                    gotit = True
            newConfigFile.write(line)
        newConfigFile.close()
        return gotit

    def _replaceConfigFile(self):

        # Save old file and rename new one
        configBak = self.configFilename + '.bak'
        print 'Backing-up old file to:', configBak
        if os.path.exists(configBak):
            os.remove(configBak)

        shutil.move(self.configFilename, configBak)
        print 'Saving new file'
        shutil.move(self.newConfigFilename, self.configFilename)
        print 'Done'

    def _openNewConfigFile(self):
        self.newConfigFilename = self.configFilename + '.new'
        return open(self.newConfigFilename, 'w')

    def _getFirstKey(self):
        # Reverse the order to process them with pop()
        self.pattern.reverse()
        return self._getNextKey()

    def _getNextKey(self):
        return self.pattern.pop()

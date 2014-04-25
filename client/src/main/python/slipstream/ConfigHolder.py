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

import copy
import slipstream.util as util
from slipstream.contextualizers.ContextualizerFactory import ContextualizerFactory


class ConfigHolder(object):
    @staticmethod
    def configFileToDict(configFileName):
        config = ConfigHolder.parseConfig(configFileName)
        _dict = ConfigHolder._convertToDict(config)
        return _dict

    @staticmethod
    def parseConfig(filename):
        return util.parseConfigFile(filename)

    @staticmethod
    def _convertToDict(config):
        dict = {}
        for section in config.sections():
            for k, v in config.items(section):
                dict[k] = v
        return dict

    @staticmethod
    def assignAttributes(obj, dictionary):
        util.assignAttributes(obj, dictionary)

    def __init__(self, options={}, config={}, context={}, configFile=''):
        # command line options
        self.options = self._extractDict(options)
        self.options['ssLogDir'] = util.REPORTSDIR
        # classes to instantiate via Factories
        self.config = config or self._getConfigFromFileAsDict(configFile)
        # SlipStream context
        self.context = context or ContextualizerFactory.getContextAsDict()

    def _getConfigFromFileAsDict(self, filename=''):
        configFileName = filename or util.getConfigFileName()
        return self.configFileToDict(configFileName)

    def _extractDict(self, obj):
        if isinstance(obj, dict):
            return obj

        _dict = {}
        for k, v in obj.__dict__.items():
            if not k.startswith('_') and not callable(v):
                _dict[k] = v
        return _dict

    def assign(self, obj):
        self.assignConfig(obj)
        self.assignOptions(obj)
        self.assignContext(obj)

    def assignConfig(self, obj):
        ConfigHolder.assignAttributes(obj, self.config)

    def assignOptions(self, obj):
        ConfigHolder.assignAttributes(obj, self.options)

    def assignContext(self, obj):
        ConfigHolder.assignAttributes(obj, self.context)

    def assignOptionsAndContext(self, obj):
        self.assignOptions(obj)
        self.assignContext(obj)

    def assignConfigAndOptions(self, obj):
        self.assignConfig(obj)
        self.assignOptions(obj)

    def set(self, key, value):
        self.options[key] = value

    def copy(self):
        return self.__copy__()

    def __copy__(self):
        return ConfigHolder(self.options.copy(), self.config.copy(),
                            self.context.copy())

    def deepcopy(self):
        return self.__deepcopy__()

    def __deepcopy__(self, memo=dict()):
        deepCopy = ConfigHolder(copy.deepcopy(self.options),
                                copy.deepcopy(self.config),
                                copy.deepcopy(self.context))
        return deepCopy

    def __str__(self):
        output = '* %s:\n' % self.__class__.__name__
        for p in ['options', 'config', 'context']:
            if getattr(self, p):
                output += '** %s:\n' % p.upper()
                output += '  %s\n' % str(getattr(self, p))
        return output

    def __getattr__(self, key):
        if key in self.options:
            source = self.options
        elif key in self.config:
            source = self.config
        elif key in self.context:
            source = self.context
        else:
            raise AttributeError('Can\'t find key: %s' % key)
        return source.get(key)

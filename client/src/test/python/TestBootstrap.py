#!/usr/bin/env python
"""
 SlipStream Client
 =====
 Copyright (C) 2015 SixSq Sarl (sixsq.com)
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

import unittest
from mock import Mock

import slipstream_bootstrap
from slipstream_bootstrap import version_in_range
from slipstream_bootstrap import _system_supports_initd
from slipstream_bootstrap import RedHat_ver_min_incl_max_excl
from slipstream_bootstrap import Ubuntu_ver_min_incl_max_excl


class TestBootstrap(unittest.TestCase):

    def test_version_in_range(self):
        assert True == version_in_range('1', ((0,), (2,)))
        assert True == version_in_range('1', ((1,), (2,)))
        assert False == version_in_range('1', ((0,), (1,)))

        assert True == version_in_range('1.2', ((1, 2), (1, 3)))

    def test_system_supports_initd_default_ranges(self):
        slipstream_bootstrap._is_linux = Mock(return_value=True)

        min_incl = RedHat_ver_min_incl_max_excl[0][0]
        slipstream_bootstrap._get_linux_distribution = Mock(return_value=('CentOS', str(min_incl), None))
        assert True == _system_supports_initd()
        slipstream_bootstrap._get_linux_distribution = Mock(return_value=('CentOS', str(min_incl - 0.1), None))
        assert False == _system_supports_initd()

        max_excl = RedHat_ver_min_incl_max_excl[1][0]
        slipstream_bootstrap._get_linux_distribution = Mock(return_value=('CentOS', str(max_excl), None))
        assert False == _system_supports_initd()
        slipstream_bootstrap._get_linux_distribution = Mock(return_value=('CentOS', str(max_excl - 0.1), None))
        assert True == _system_supports_initd()

        min_incl = Ubuntu_ver_min_incl_max_excl[0][0]
        slipstream_bootstrap._get_linux_distribution = Mock(return_value=('Ubuntu', str(min_incl), None))
        assert True == _system_supports_initd()
        slipstream_bootstrap._get_linux_distribution = Mock(return_value=('Ubuntu', str(min_incl - 0.1), None))
        assert False == _system_supports_initd()

        max_excl = Ubuntu_ver_min_incl_max_excl[1][0]
        slipstream_bootstrap._get_linux_distribution = Mock(return_value=('Ubuntu', str(max_excl), None))
        assert False == _system_supports_initd()
        slipstream_bootstrap._get_linux_distribution = Mock(return_value=('Ubuntu', str(max_excl - 0.1), None))
        assert True == _system_supports_initd()

    def test_system_supports_initd(self):
        slipstream_bootstrap._is_linux = Mock(return_value=False)
        assert False == _system_supports_initd()

        slipstream_bootstrap._is_linux = Mock(return_value=True)
        slipstream_bootstrap._get_linux_distribution = Mock(return_value=('foo', '0', None))
        assert False == _system_supports_initd()

        for ver in ['0', '4.0', '8']:
            slipstream_bootstrap._get_linux_distribution = Mock(return_value=('CentOS', ver, None))
            assert False == _system_supports_initd()


if __name__ == '__main__':
    unittest.main()

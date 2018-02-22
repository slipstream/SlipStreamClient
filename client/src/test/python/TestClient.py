#!/usr/bin/env python
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

import unittest
from mock import Mock

from slipstream.Client import Client
from slipstream.NodeDecorator import NodeDecorator
from slipstream.ConfigHolder import ConfigHolder


def rtp_index(rtp):
    return int(rtp.split('.')[1].split(':')[0])


def get_rtp_all(side_effect, no_block=False):
    ch = ConfigHolder()
    ch.set('noBlock', no_block)
    ch.set('timeout', 1)
    ch.set('verboseLevel', 3)
    ch.set('endpoint', 'https://foo.bar')
    Client._getRuntimeParameter = Mock(side_effect=side_effect)
    client = Client(ch)
    client.httpClient.getRuntimeParameter = Mock(side_effect=side_effect)
    return client.get_rtp_all('foo', 'bar')


class TestClient(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_do_not_qualify_parameter(self):
        orch_node_name = NodeDecorator.orchestratorName + '-cloudX'
        orch_param = orch_node_name + \
                     NodeDecorator.NODE_PROPERTY_SEPARATOR + \
                     'foo'

        context = {NodeDecorator.NODE_INSTANCE_NAME_KEY: orch_node_name}
        ch = ConfigHolder(context=context, config={'bar': 'baz', 'endpoint': 'https://foo.bar'})
        c = Client(ch)
        assert orch_param == c._qualifyKey(orch_param)

    def test_get_rtp_all_success(self):
        nrtps = 3
        ids = map(str, range(1, nrtps + 1))
        rtps = dict(map(lambda i: ('foo.%s:bar' % i, i), ids))

        def get_rtp(rtp):
            if rtp.endswith('ids'):
                return ','.join(ids)
            else:
                return rtps[rtp]

        params = get_rtp_all(get_rtp, no_block=False)

        assert isinstance(params, list)
        assert len(params) == nrtps
        for p, v in params:
            i = rtp_index(p)
            assert i == int(v)

    def test_get_rtp_all_allnotset_timeout(self):
        nrtps = 3
        ids = map(str, range(1, nrtps + 1))
        rtps = dict(map(lambda i: ('foo.%s:bar' % i, None), ids))

        def get_rtp(rtp):
            if rtp.endswith('ids'):
                return ','.join(ids)
            else:
                return rtps[rtp]

        params = get_rtp_all(get_rtp, no_block=False)

        assert isinstance(params, list)
        assert len(params) == nrtps
        for _, v in params:
            assert '' == v

    def test_get_rtp_all_somenotset_notimeout(self):

        def gen_rtp(i):
            return 'foo.%s:bar' % i, i if (int(i) % 2 == 0) else None

        nrtps = 25
        ids = map(str, range(1, nrtps + 1))
        rtps = dict(map(gen_rtp, ids))

        def get_rtp(rtp):
            if rtp.endswith('ids'):
                return ','.join(ids)
            else:
                return rtps[rtp]

        params = get_rtp_all(get_rtp, no_block=True)

        assert isinstance(params, list)
        assert len(params) == nrtps
        for p, v in params:
            i = rtp_index(p)
            if i % 2 == 0:
                assert i == int(v)
            else:
                assert '' == v


if __name__ == '__main__':
    unittest.main()

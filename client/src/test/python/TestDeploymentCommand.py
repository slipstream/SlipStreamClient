import unittest

from slipstream.command.DeploymentCommandBase import split_key


class TestDeploymentCommandBase(unittest.TestCase):

    def test_split_key(self):
        assert (None, None, '') == split_key('')
        assert (None, None, 'bar') == split_key('bar')
        assert ('foo', None, 'bar') == split_key('foo:bar')
        assert ('ss', None, 'bar') == split_key('ss:bar')
        assert ('foo', '1', 'bar') == split_key('foo.1:bar')


if __name__ == '__main__':
    unittest.main()
import subprocess
import unittest
from mock import Mock

from slipstream import util


class TestUtil(unittest.TestCase):

    def test_execute(self):
        status = util.execute(['sleep', '1'])
        self.assertEqual(status, 0)

        process = util.execute(['sleep', '3'], noWait=True)
        self.assertTrue(isinstance(process, subprocess.Popen))
        process.kill()

    def xtest_execute_apple_specific(self):
        status, err = util.execute(['sleep'], withStderr=True)
        self.assertEqual(status, 1)
        self.assertEqual(err, 'usage: sleep seconds\n')

        status, out = util.execute(['sleep'], withOutput=True)
        self.assertEqual(status, 1)
        self.assertEqual(out, 'usage: sleep seconds\n')

    def test_sanitize_env(self):
        assert {} == util._sanitize_env({})
        assert 'a' == util._sanitize_env({'a': 'a'})['a']
        assert '' == util._sanitize_env({'a': None})['a']
        assert '0' == util._sanitize_env({'a': 0})['a']
        assert 'True' == util._sanitize_env({'a': True})['a']

    def test_sanitize_env_on_execute(self):
        try:
            util.execute(['true'], extra_env={'a': None})
        except TypeError:
            self.fail('Should not raise TypeError.')

        def _sanitize_env_mocked(env):
            return env
        _sanitize_env_save = util._sanitize_env
        util._sanitize_env = Mock(side_effect=_sanitize_env_mocked)
        try:
            self.assertRaises(TypeError, util.execute, *(['true'],),
                              **{'extra_env': {'a': None}})
            try:
                util.execute(['true'], extra_env={'a': None})
            except TypeError as ex:
                assert 'execve() arg 3 contains a non-string value' == str(ex)
        finally:
            util._sanitize_env = _sanitize_env_save


if __name__ == "__main__":
    unittest.main()

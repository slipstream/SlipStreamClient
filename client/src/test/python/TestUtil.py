import subprocess
import unittest

from slipstream import util


class TestUtil(unittest.TestCase):

    def test_execute(self):
        status = util.execute(['sleep', '1s'])
        self.assertEqual(status, 0)

        process = util.execute(['sleep', '3s'], noWait=True)
        self.assertIsInstance(process, subprocess.Popen)
        process.kill()

        status, err = util.execute(['sleep'], withStderr=True)
        self.assertEqual(status, 1)
        self.assertEqual(err, 'usage: sleep seconds\n')

        status, out = util.execute(['sleep'], withOutput=True)
        self.assertEqual(status, 1)
        self.assertEqual(out, 'usage: sleep seconds\n')

if __name__ == "__main__":
    unittest.main()

import re

from daemon.runner import is_pidfile_stale
from daemon.runner import DaemonRunner as BaseDaemonRunner
from daemon.runner import DaemonRunnerStopFailureError
from lockfile import LockTimeout

class DaemonRunner(BaseDaemonRunner):

    def _status(self):
        app_name = self.app.get_app_name()

        pid = self.pidfile.read_pid()

        if not pid:
            print "%s is not running" % app_name
            return

        if is_pidfile_stale(self.pidfile):
            print "%s is not running. Stale PID file %s" % (app_name,
                                                            self.pidfile.path)
        else:
            print "%s (pid %s) is running..." % (app_name, pid)

    action_funcs = dict(BaseDaemonRunner.action_funcs.items() + [(u'status', _status)])

    def __init__(self, runnable):
        """slipstream.daemonr.DaemonRunnable.DaemonRunnable
        :param runnable: Runnable object
        :type runnable: subclass from slipstream.daemonr.DaemonRunnable.DaemonRunnable to get required interface."""
        self._action = ''

        try:
            if runnable.get_action():
                self.run_action(runnable)
            else:
                runnable.run()
        except Exception:
            import traceback
            runnable.get_logger().critical(traceback.format_exc())
            raise

    def set_action(self, action):
        self._action = action

    def get_action(self):
        return self._action

    def parse_args(self):
        self.action = self.get_action()

    def run_action(self, runnable):
        action = runnable.get_action()
        self.set_action(action)

        super(DaemonRunner, self).__init__(runnable)
        self.daemon_context.files_preserve = runnable.get_filedescriptors()
        try:
            self.do_action()
        except DaemonRunnerStopFailureError as ex:
            if 'stop' == action:
                raise SystemExit('Failed to stop: %s' % ex)
            elif 'restart' == action and re.search('PID file.*not locked', str(ex)):
                self._start()
            else:
                raise ex
        except LockTimeout as ex:
            if 'start' == action:
                print 'Failed to start: %s' % ex
            else:
                raise ex


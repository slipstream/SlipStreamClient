import os
import sys

class DaemonRunnable(object):
    def __init__(self, config_holder):
        self.pidfile_path = '/tmp/daemonrunnable.pid'

        config_holder.assign(self)
        self.config_holder = config_holder

        # For DaemonRunner
        self.stdin_path = '/dev/null'
        self.stdout_path = self.log_file
        self.stderr_path = self.log_file
        self.pidfile_timeout = -1

    def run(self):
        raise NotImplementedError()
    
    def get_logger(self):
        raise NotImplementedError()

    def get_action(self):
        raise NotImplementedError()

    def get_filedescriptors(self):
        "Provide a list of file descriptors not to be touched by DaemonRunner."
        return self._get_logger_filedescriptors()

    def _get_logger_filedescriptors(self):
        fds = []
        for h in self.get_logger().handlers:
            try:
                fds.append(h.stream.fileno())
            except:
                pass
        return fds

    def get_app_name(self):
        return os.path.basename(sys.argv[0])

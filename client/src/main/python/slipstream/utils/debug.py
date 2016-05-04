import re
import sys
import threading
import linecache


class _tracer(object):

    def _traceit(self, frame, event, arg):
        if event == "line" or event == "call":
            name = frame.f_globals["__name__"] or '<Unknown>'
            if self.packages_filter is None or self.packages_filter.search(name):
                lineno = frame.f_lineno
                filename = frame.f_globals.get("__file__", '')
                if (filename.endswith(".pyc") or
                    filename.endswith(".pyo")):
                    filename = filename[:-1]
                line = linecache.getline(filename, lineno)
                thread = threading.current_thread()
                print '\033[95mThread \033[94m{0: <35} \033[36m{1: <60} \033[95m-> \033[37m{2}\033[0m'.format('%s (%s)' % (thread.name, thread.ident),
                                                                                                               '%s:%s' % (name, lineno),
                                                                                                               line.rstrip())
        return self._traceit

    def set_filter(self, packages_filter=None):
        try:
            self.packages_filter = re.compile(packages_filter)
        except:
            self.packages_filter = None

    def __init__(self, packages_filter=None):
        self.set_filter(packages_filter)
        self.thread_local = threading.local()
        self.thread_local.trace_backup = []
        self.thread_local.trace_backup.append(sys.gettrace())

    def __call__(self, enable=True):
        if enable:
            try:
                self.thread_local.trace_backup.append(sys.gettrace())
            except AttributeError:
                self.thread_local.trace_backup = []
                self.thread_local.trace_backup.append(sys.gettrace())
            sys.settrace(self._traceit)
        else:
            sys.settrace(self.thread_local.trace_backup.pop())

    def __enter__(self):
        self(True)

    def __exit__(self, type, value, traceback):
        self(False)

trace = _tracer()



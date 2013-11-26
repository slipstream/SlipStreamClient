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

import sys
import Queue
from threading import Thread

__all__ = ['TasksRunner']


class TasksRunner(object):
    QUEUE_GET_TIMEOUT = 2

    def __init__(self):
        self.threads = []
        self.exc_queue = Queue.Queue()

    def run_task(self, target, args=(), name=None):
        thr = ThreadWrapper(target=target, args=args, name=name,
                            exc_queue=self.exc_queue)
        self.threads.append(thr)
        thr.start()

    def wait_tasks_finished(self):
        while not self._tasks_finished():
            self._process_exc_queue()
        self._process_exc_queue()

    def _tasks_finished(self):
        return all(map(lambda x: not x.is_alive(), self.threads))

    def _process_exc_queue(self):
        try:
            exc_info = self.exc_queue.get(block=True,
                                          timeout=self.QUEUE_GET_TIMEOUT)
        except Queue.Empty:
            pass
        else:
            self._stop_all_threads()
            raise exc_info[0], exc_info[1], exc_info[2]

    def _stop_all_threads(self):
        for t in self.threads:
            t._Thread__stop()


class ThreadWrapper(Thread):
    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs=None, verbose=None, exc_queue=None):
        super(ThreadWrapper, self).__init__(group=group, target=target,
                                            name=name, args=args,
                                            kwargs=kwargs, verbose=verbose)
        if exc_queue and not hasattr(exc_queue, 'put'):
            raise TypeError('exc_queue object must support queue interface put()')
        self.exc_queue = exc_queue
        self.exc_info = None

    def run(self):
        try:
            super(ThreadWrapper, self).run()
        except:
            if self.exc_queue is not None:
                self.exc_queue.put(sys.exc_info())
            self.exc_info = sys.exc_info()

    def get_exc_info(self):
        return self.exc_info

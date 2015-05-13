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

import sys
import Queue
from threading import Thread

__all__ = ['TasksRunner']

DEFAULT_WORKERS_NUMBER = 20
QUEUE_GET_TIMEOUT = 3


class TasksRunner(object):

    def __init__(self, task_executor=None, max_workers=None, verbose=None,
                 daemonic_workers=True):
        self._executor = task_executor
        self._max_workers = (max_workers == None) and DEFAULT_WORKERS_NUMBER \
            or int(max_workers)
        self._verbose = verbose
        self.workers = []
        self.daemonic_workers = daemonic_workers
        self.tasks_queue = Queue.Queue()
        # Queue with exceptions from threads.
        self.exc_queue = Queue.Queue()

    def put_task(self, *args):
        self.tasks_queue.put(args, timeout=10)

    def run_tasks(self):
        ntasks = self.tasks_queue.qsize()
        nworkers = (ntasks < self._max_workers) and ntasks or self._max_workers
        for _ in range(nworkers):
            worker = Worker(self._executor, self.tasks_queue)
            thr = ThreadWrapper(target=worker.work, exc_queue=self.exc_queue,
                                verbose=self._verbose, daemonic=self.daemonic_workers)
            self.workers.append(thr)
            thr.start()

    def wait_tasks_processed(self, ignore_exception=False):
        while not self._tasks_finished():
            self._process_exc_queue(ignore_exception)
        self._process_exc_queue(ignore_exception)

    def _tasks_finished(self):
        return all(map(lambda w: not w.is_alive(), self.workers))

    def _process_exc_queue(self, ignore_exception):
        try:
            exc_info = self.exc_queue.get(block=True,
                                          timeout=QUEUE_GET_TIMEOUT)
        except Queue.Empty:
            pass
        else:
            if not ignore_exception:
                self._stop_all_workers()
                raise exc_info[0], exc_info[1], exc_info[2]

    def _stop_all_workers(self):
        for t in self.workers:
            t._Thread__stop()


class Worker(object):

    def __init__(self, task_executor, tasks_queue):
        self._executor = task_executor
        self._queue = tasks_queue

    def work(self):
        while True:
            try:
                task = self._queue.get(timeout=QUEUE_GET_TIMEOUT)
            except Queue.Empty:
                break
            self._executor(*task)
            self._queue.task_done()


class ThreadWrapper(Thread):
    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs=None, verbose=None, exc_queue=None,
                 daemonic=True):
        if verbose != None and int(verbose) >= 3:
            verbose = True
        super(ThreadWrapper, self).__init__(group=group, target=target,
                                            name=name, args=args,
                                            kwargs=kwargs, verbose=verbose)
        self.setDaemon(daemonic)
        if exc_queue and not hasattr(exc_queue, 'put'):
            raise TypeError('exc_queue object must support queue interface put()')
        self.exc_queue = exc_queue
        self.exc_info = None

    def run(self):
        try:
            self._note('Starting run()')
            super(ThreadWrapper, self).run()
            self._note('Finished run()')
        except:
            self._note('Exception %s', sys.exc_info())
            if self.exc_queue is not None:
                self.exc_queue.put(sys.exc_info())
            self.exc_info = sys.exc_info()

    def get_exc_info(self):
        return self.exc_info

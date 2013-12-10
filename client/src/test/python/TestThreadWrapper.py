#!/usr/bin/env python
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

import time
import Queue
from mock import Mock
import unittest

from slipstream.utils.tasksrunner import ThreadWrapper, TasksRunner

EXCEPTION = IOError
EXCEPTION_MESSAGE = "Foo bar baz"


class _ExplodeClass(object):
    def __init__(self):
        self.test_var = 0

    def explode(self, val):
        self.test_var = val
        raise EXCEPTION(EXCEPTION_MESSAGE)


def _assert_exc_info(exc_info):
    assert isinstance(exc_info, tuple)
    assert len(exc_info) == 3
    assert exc_info[0] == EXCEPTION
    assert isinstance(exc_info[1], EXCEPTION)
    assert exc_info[1].args == (EXCEPTION_MESSAGE,)


class TestThreadWrapper(unittest.TestCase):

    def testCatchExceptionInFunction(self):
        self._run_target_and_assert(Mock(side_effect=EXCEPTION(EXCEPTION_MESSAGE)))

    def testCatchExceptionInClassMethod(self):
        expl = _ExplodeClass()
        self._run_target_and_assert(expl.explode, args=(1,))
        assert expl.test_var == 1

    def testExceptionQueued(self):
        queue = Queue.Queue()
        expl = _ExplodeClass()
        self._run_target_and_assert(expl.explode, args=(1,), exc_queue=queue)
        assert expl.test_var == 1
        _assert_exc_info(queue.get())

    def _run_target_and_assert(self, target, args=(), exc_queue=None):
        thr = ThreadWrapper(target=target, args=args, exc_queue=exc_queue)
        thr.start()
        while thr.is_alive():
            time.sleep(1)
        _assert_exc_info(thr.get_exc_info())


class TestTasksRunner(unittest.TestCase):
    def testRunTaskNoExceptions(self):
        tr = TasksRunner()
        tr.QUEUE_GET_TIMEOUT = 1
        ntasks = 3
        for _ in range(ntasks):
            tr.run_task(Mock())
        tr.wait_tasks_finished()
        assert tr._tasks_finished() is True
        assert len(tr.threads) == ntasks

    def testQueueExceptionsManualCheck(self):
        tr = TasksRunner()
        ntasks = 3
        for _ in range(ntasks):
            tr.run_task(Mock(side_effect=EXCEPTION(EXCEPTION_MESSAGE)))
        while not tr._tasks_finished():
            time.sleep(1)
        assert tr._tasks_finished() is True
        assert len(tr.threads) == ntasks
        assert tr.exc_queue.qsize() == ntasks
        for _ in range(ntasks):
            _assert_exc_info(tr.exc_queue.get())

    def testQueueExceptionsRaises(self):
        tr = TasksRunner()
        ntasks = 3
        for _ in range(ntasks):
            tr.run_task(Mock(side_effect=EXCEPTION(EXCEPTION_MESSAGE)))
        self.failUnlessRaises(EXCEPTION, tr.wait_tasks_finished)

"""
 SlipStream Client
 =====
 Copyright (C) 2015 SixSq Sarl (sixsq.com)
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

from slipstream.utils.tasksrunner import TasksRunner


class VmScaler(object):

    def __init__(self, task_executor, max_workers, verbose_level):
        self._task_executor = task_executor
        self._max_workers = max_workers
        self._verbose_level = verbose_level

        self._tasks_runner = None

    def set_tasks_and_run(self, nodes_instances, done_reporter):
        """
        :param nodes_instances: list of node instances
        :type nodes_instances: list [NodeInstance, ]
        :param done_reporter: function that reports back to SlipStream
        :type done_reporter: callable with signature `done_reporter(<NoneInstance>)`
        """
        self._tasks_runner = TasksRunner(self._task_executor,
                                         max_workers=self._max_workers)
        for node_instance in nodes_instances:
            self._tasks_runner.put_task(node_instance, done_reporter)

        self._tasks_runner.run_tasks()

    def wait_tasks_finished(self):
        if self._tasks_runner is not None:
            self._tasks_runner.wait_tasks_processed()

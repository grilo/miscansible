# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import time
import collections
import ansible.plugins.callback


class CallbackModule(ansible.plugins.callback.CallbackBase):

    """
    Ansible callback plugin for playbook and task execution times
    """
    CALLBACK_VERSION = 2.0
    CALLBACK_NAME = 'benchmark_ing'
    CALLBACK_NEEDS_WHITELIST = False

    def __init__(self, *args, **kwargs):
        super(CallbackModule, self).__init__(*args, **kwargs)
        self._running_tasks = collections.OrderedDict()
        self._playbook_start = time.time()

    def _tracktask(self, key, task):
        uuid = str(task._uuid)
        if uuid not in self._running_tasks.keys():
            self._running_tasks[uuid] = {}
            self._running_tasks[uuid]['name'] = str(task).split(": ", 1)[1]
        self._running_tasks[uuid][key] = time.time()
        if key == "stop":
            delta = self._running_tasks[uuid]['stop'] - self._running_tasks[uuid]['start']
            self._display.display("Finished in (%.3f) seconds" % (delta), color='cyan')

    # Initialize the counter
    def v2_playbook_on_task_start(self, task, is_conditional):
        self._tracktask('start', task)

    def v2_runner_on_failed(self, result, ignore_errors=False):
        self._tracktask('stop', result._task)
    def v2_runner_on_ok(self, result):
        self._tracktask('stop', result._task)
    def v2_runner_on_unreachable(self, result):
        self._tracktask('stop', result._task)
    def v2_runner_on_async_ok(self, host, result):
        self._tracktask('stop', result._task)
    def v2_runner_on_async_failed(self, result):
        self._tracktask('stop', result._task)

    def v2_playbook_on_stats(self, stats):
        self._display.banner("BENCHMARK".upper())
        self._display.display("Playbook: %.3f seconds." % (time.time() - self._playbook_start), color='purple')
        for k, v in self._running_tasks.items():
            delta = v['stop'] - v['start']
            color = 'cyan'
            if 3 < delta <= 30:
                color = 'green'
            elif 30 < delta <= 300:
                color = 'yellow'
            elif delta > 300:
                color = 'red'
            self._display.display("\tTask [%s]: %.3f seconds." % (v['name'], delta), color=color)

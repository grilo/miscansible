from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import ansible.plugins.callback
try:
    import simplejson as json
except ImportError:
    import json


class CallbackModule(ansible.plugins.callback.CallbackBase):

    """
    Ansible callback plugin for human-readable result logging
    """
    CALLBACK_VERSION = 2.0
    CALLBACK_NAME = 'log_ing'
    CALLBACK_NEEDS_WHITELIST = False

    # Fields to reformat output for
    LOGFIELDS = ['start', 'cmd', 'command', 'msg', 'stdout', 'stderr', 'results', 'end', 'delta']

    def _format_output(self, output):
        # If output is a dict
        if type(output) == dict:
            output = json.dumps(output, indent=2)
        elif type(output) == unicode:
            # Strip unicode
            output = output.encode('ascii', 'replace')
        # If output is a list, recurse
        elif type(output) == list:
            output = "\n".join([self._format_output(i) for i in output])
        return str(output)

    def human_log(self, data):
        if type(data) != dict: return
        if data.get('_ansible_no_log') == True: return

        for f in CallbackModule.LOGFIELDS:
            if f not in data: continue
            self._display.display("(%s) %s" % (f, self._format_output(data[f])))

    def v2_runner_on_ok(self, result):
        if self._display.verbosity > 0:
            self.human_log(result._result)
    def v2_runner_on_async_ok(self, host, result):
        if self._display.verbosity > 0:
            self.human_log(result._result)
    def v2_runner_on_async_poll(self, result):
        if self._display.verbosity > 0:
            self.human_log(result._result)

    def v2_runner_on_failed(self, result, ignore_errors=False):
        self.human_log(result._result)
    def v2_runner_on_async_failed(self, result):
        self.human_log(result._result)
    def v2_runner_on_unreachable(self, result):
        self.human_log(result._result)


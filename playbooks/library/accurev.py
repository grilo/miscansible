#!/usr/bin/python
# -*- coding: utf-8 -*-

import re
import shlex
import os
import shutil


class AccuRev(object):

    commands = {
        'workspace': {
            'create': 'mkws -w',
            'change': 'chws -w',
            'remove': 'wspace',
        },
        'reftree': {
            'create': 'mkref -r',
            'change': 'chref -r',
            'remove': 'reftree',
        },
    }

    def __init__(self, module, dest, stream_type, depot, stream, username, password, executable):
        self.module = module
        self.dest = dest
        self.stream_type = stream_type
        self.name = os.path.basename(dest)
        self.depot = depot
        self.stream = stream
        self.username = username
        self.password = password
        self.executable = executable

    def _cmd(self, command, check_rc=True):
        owd = os.getcwd()
        os.chdir(self.dest)

        command = ' '.join([self.executable, command])
        rc, out, err = self.module.run_command(shlex.split(command), check_rc)

        os.chdir(owd)
        return (rc, out, err)

    def login(self):
        _, out, _ = self._cmd('info')
        if re.match('Username:', out):
            self._cmd('login %s %s' % (self.username, self.password))
        return True

    def create(self):
        cmd = AccuRev.commands[self.stream_type]['create']
        cmd += ' "%s" -b "%s" -l .' % (self.name, self.stream)
        rc, out, err = self._cmd(cmd)
        if "already exists" in err:
            rc, out, err = self.change()
            if rc != 0:
                raise Exception("Unable to create nor change the workspace/reftree.")

    def change(self):
        cmd = AccuRev.commands[self.stream_type]['change']
        cmd += ' "%s" -b "%s" -l .' % (self.name, self.stream)
        self._cmd(cmd)

    def update(self, force=False):
        if not force:
            return self._cmd('update')
        self._cmd('update -9')
        self._cmd('pop -R -O .')

    def remove(self):
        cmd = 'remove %s' % AccuRev.commands[self.stream_type]['remove']
        cmd += ' %s' % (self.name)
        rc, out, err = self._cmd(cmd)
        if rc != 0:
            raise Exception("Unable to remove the workspace/reftree.")

# ===========================================

def main():
    module = AnsibleModule(
        argument_spec=dict(
            dest=dict(required=True, type='path'),
            stream_type=dict(required=False, default='workspace'),
            depot=dict(required=True),
            stream=dict(default=None),
            force=dict(default=False, type='bool'),
            state=dict(default='exists', required=False),
            username=dict(required=False),
            password=dict(required=False),
            executable=dict(default=None, type='path'),
        ),
        supports_check_mode=False
    )

    dest = module.params['dest']
    stream_type = module.params['stream_type']
    depot = module.params['depot']
    stream = module.params['stream']
    force = module.params['force']
    state = module.params['state']
    username = module.params['username']
    password = module.params['password']
    executable = module.params['executable'] or module.get_bin_path('accurev', True)

    # Sanity check
    if not os.path.isdir(dest):
        module.fail_json(msg="dest parameter (%s) must be a valid directory." % (dest))
    elif not dest.startswith("/") and not re.match('[A-Za-z]+:', dest):
        module.fail_json(msg="dest parameter (%s) must be an absolute path." % (dest))

    accurev = AccuRev(module, dest, stream_type, depot, stream, username, password, executable)
    accurev.login()

    if state == 'absent':
        accurev.remove()
    else:
        accurev.create()
        accurev.update(force)
    module.exit_json(changed=True, dest=dest, desttype=desttype, state=state)

# import module snippets
from ansible.module_utils.basic import *
main()

#!/usr/bin/python
# -*- coding: utf-8 -*-

import re
import shlex
import os
import shutil


class AccuRev(object):

    def __init__(self, module, dest, depot, stream, username, password, executable):
        self.module = module
        self.dest = dest
        self.definition = self._get_definition()
        self.name = os.path.basename(dest)
        self.depot = depot
        self.stream = stream
        self.username = username
        self.password = password
        self.executable = executable

    def _command(self, command, check_rc=True):
        command = ' '.join([self.executable, command])
        rc, out, err = self.module.run_command(shlex.split(command), check_rc)
        if rc != 0:
            raise Exception
        return (rc, out, err)

    def _command_in_dir(self, path, command):
        owd = os.getcwd()
        os.chdir(path)
        result = self._command(command)
        os.chdir(owd)
        return result

    def _get_definition(self):
        # I should parse the XML output and confirm that the workspace/reftree
        # exists. If it does, it should match the given type, otherwise we
        # should throw an exception and abort immediately.
        rc, out, err = self._command('accurev show -p %s streams' % (depot))

    def is_logged_in(self):
        self._command('info')

    def login(self):
        self._command('login %s %s' % (self.username, self.password))

    def is_workspace(self):
        rc, out, err = self._command_in_dir(self.dest, 'info')

    def change(self):
        # Delete the old location
        if self.is_workspace(self.dest) and re.match('[A-Za-z0-9]+', self.dest):
            shutil.rmtree(self.definition['location'])

        cmd = ''
        if self.definition['type'] == 'workspace':
            cmd = 'chws -w'
        elif self.definition['type'] == 'reftree':
            cmd = 'chref -r'
        else: raise Exception
        cmd += '"%s" -b "%s" -l "%s"' % (self.name, self.stream, self.dest)
        self._command(cmd)

    def create(self):
        cmd = ''
        if self.definition['type'] == 'workspace':
            cmd = 'mkws -w'
        elif self.definition['type'] == 'reftree':
            cmd = 'mkref -r'
        else: raise Exception
        cmd += '"%s" -b "%s" -l "%s"' % (self.name, self.stream, self.dest)
        self._command(cmd)

    def remove(self):
        cmd = 'remove '
        if self.definition['type'] == 'workspace':
            cmd += 'wspace '
        elif self.definitioin['type'] == 'reftree':
            cmd += 'reftree '
        else: raise Exception
        cmd += self.name
        self._command(cmd)

    def update(self, path, force=False):
        if not force:
            return self._command_in_dir(self.dest, 'update')

        # Make sure we're not deleting anything we shouldn't
        if self.is_workspace(path) and re.match('[A-Za-z0-9]+', path):
            shutil.rmtree(path)
            self._command_in_dir(self.dest, 'update -9')
            self._command_in_dir(self.dest, 'pop -R -O .')
        else:
            raise Exception

# ===========================================

def main():
    module = AnsibleModule(
        argument_spec=dict(
            dest=dict(required=True, type='path'),
            desttype=dict(required=False, default='workspace'),
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
    desttype = module.params['desttype']
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

    accurev = AccuRev(module, dest, depot, stream, username, password, executable)

    if not accurev.is_logged_in():
        accurev.login()

    if desttype == 'workspace':
        if state == 'absent' and accurev.is_workspace():
            accurev.remove_workspace()
        elif not accurev.is_workspace():
            accurev.create_workspace()
    elif desttype == 'reftree':
        if state == 'absent' and accurev.is_reftree():
            accurev.remove_workspace()
        if not accurev.is_reftree():
            accurev.create_reftree()
    else:
        module.fail_json(msg="desttype parameter (%s) has an unknown value." % (desttype))
    module.exit_json(changed=True, dest=dest, desttype=desttype, state=state)

# import module snippets
from ansible.module_utils.basic import *
main()

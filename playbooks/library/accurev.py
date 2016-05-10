#!/usr/bin/python
# -*- coding: utf-8 -*-

# (c) 2016, Joao Grilo <joao.grilo@gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

DOCUMENTATION = '''
---
module: accurev
short_description: Deploys an accurev repository.
description:
   - Deploys a workspace/reftree in dest. If dest exists, update to the
     workspace/reftree, otherwise create it.
version_added: "1.0"
author: "Joao Grilo (@jmgnm) <joao.grilo@gmail.com>"
notes:
   - Requires a working/configured AccuRev client installed on the destination
     host.
requirements: []
options:
  dest:
    description:
      - Absolute path where the workspace/reftree should be deployed.
    required: true
    default: null
  stream_type:
    description:
      - The type of stream to create.
    required: false
    default: "workspace"
    choises: ["workspace", "reftree"]
  force:
    description:
      - If C(True), the files on the destination will be updated regardless of
        current state. If C(False), a normal update will be executed.
    required: false
    default: "False"
    choices: [ "True", "False" ]
  username:
    description:
      - Username parameter passed to AccuRev to login with prior to running the
        commands.
    required: false
    default: null
  password:
    description:
      - Password parameter passed to AccuRev to login with prior to running the
        commands.
    required: false
    default: null
  executable:
    required: false
    default: null
    description:
      - Path to the AccuRev executable to use. If not supplied, the normal
        the normal mechanism for resolving binary paths will be used.
  state:
    required: false
    default: "exists"
    choices: [ "exists", "absent" ]
    description:
      - If C(exists), create the workspace/reftree. If C(absent) delete the
        workspace/reftree from the filesystem and from AccuRev.
'''

EXAMPLES = '''
# Create a workspace in the specified folder
- accurev: dest=/var/scm/accurev/WS_BRANCH stream=SOME_BRANCH
# Forcefully update a reference tree in the specified folder, with explicit
# login credentials and accurev binary path
- accurev: dest=/home/user/reftrees/RF_ANOTHERBRANCH stream=SOMETHING username=hello password=world executable=/opt/accurev/bin/accurev force=True
# Remove a workspace from the filesystem and disable it in AccuRev
- accurev: dest=/home/user/workspaces/WS_TEST state=absent
'''
 
import re
import os
 
 
class AccuRev(object):
 
    commands = {
        'workspace': {
            'create': ['mkws', '-w'],
            'change': ['chws', '-w'],
            'remove': ['wspace'],
        },
        'reftree': {
            'create': ['mkref', '-r'],
            'change': ['chref', '-r'],
            'remove': ['reftree'],
        },
    }
 
    def __init__(self, module, dest, stream_type, stream, username, password, executable):
        self.module = module
        self.dest = dest
        self.stream_type = stream_type
        self.name = os.path.basename(dest)
        self.stream = stream
        self.username = username
        self.password = password
        self.executable = executable
 
    def _cmd(self, args, check_rc=False):
        owd = os.getcwd()
        os.chdir(self.dest)
 
        command = [self.executable]
        command.extend(args)
        rc, out, err = self.module.run_command(command, check_rc)
 
        os.chdir(owd)
        return (rc, out, err)
 
    def login(self):
        _, out, _ = self._cmd(['info'])
        if not re.match('Username:', out):
            self._cmd(['login', self.username, self.password], True)
        return True
 
    def create(self):
        cmd = AccuRev.commands[self.stream_type]['create']
        cmd.extend([self.name, '-b', self.stream, '-l', '.'])
        rc, out, err = self._cmd(cmd)
        if "already" in err:
            rc, out, err = self.change()
            if rc != 0:
                raise Exception("Unable to create nor change the workspace/reftree.")
 
    def change(self):
        cmd = AccuRev.commands[self.stream_type]['change']
        cmd.extend([self.name, '-b', self.stream, '-l', '.'])
        return self._cmd(cmd)
 
    def update(self, force=False):
        if not force:
            return self._cmd(['update'], True)
        self._cmd(['update', '-9'], True)
        self._cmd(['pop', '-R', '-O', '.'], True)
 
    def remove(self):
        cmd = ['remove'].extend(AccuRev.commands[self.stream_type]['remove'])
        cmd.extend(self.name)
        rc, out, err = self._cmd(cmd)
        if rc != 0:
            raise Exception("Unable to remove the workspace/reftree.")
 
# ===========================================
 
def main():
    module = AnsibleModule(
        argument_spec=dict(
            dest=dict(required=True, type='path'),
            stream_type=dict(required=False, default='workspace'),
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
    stream = module.params['stream']
    force = module.params['force']
    state = module.params['state']
    username = module.params['username']
    password = module.params['password']
    executable = module.params['executable'] or module.get_bin_path('accurev', True)
 
    # Sanity check
    if not os.path.isabs(dest):
        module.fail_json(msg="dest parameter (%s) must be an absolute path." % (dest))
    elif os.path.dirname(dest) == dest:
        module.fail_json(msg="dest parameter (%s) can't be a root directory." % (dest))


    if not os.path.isdir(dest):
        os.makedirs(dest)

    accurev = AccuRev(module, dest, stream_type, stream, username, password, executable)
    if not accurev.login():
        module.fail_json(msg="Unable to login to AccuRev with user (%s)." % (username))
 
    if state == 'absent':
        accurev.remove()
    else:
        accurev.create()
        accurev.update(force)
    module.exit_json(changed=True, dest=dest, stream_type=stream_type, state=state)
 
from ansible.module_utils.basic import *
main()

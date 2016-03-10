#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import shutil
import subprocess
import hashlib


def string_in_file(path, needle):
    if not os.path.isfile(path): return False
    with open(path) as f:
        for line in f:
            if needle in line: return True
    return False

def make_sshcfg(cfg, host, user, key):
    with open(sshconfig, 'a') as cfg:
        cfg.write("""Host %s
    HostName %s
    User %s
    IdentityFile %s
    IdentitiesOnly yes
""" % (host, host, user, key))

def digest(path):
    with open(path, 'rb') as f:
        return hashlib.sha1(f.read()).hexdigest()

def main():

    module = AnsibleModule(
        argument_spec = dict(
            rootdir = dict(type='path', default=None),
            project = dict(default=None),
            remote = dict(required=False, default=None),
            privatekey = dict(type='path', required=False, default=None),
            state = dict(required=False, default='present'),
        )
    )

    rootdir = module.params["rootdir"]
    project = module.params["project"]
    remote = module.params["remote"]
    privatekey = module.params["privatekey"]
    state = module.params["state"]

    project_dir = os.path.join(rootdir, project)

    # Sanity check
    if not os.path.isdir(rootdir):
        module.fail_json(msg="Rootdir parameter (%s) must be a valid directory." % (rootdir))
    if project is None:
        module.fail_json(msg="Project parameter (%s) is mandatory and a valid string." % (project))
    if privatekey is not None:
        if not os.path.isfile(privatekey):
            module.fail_json(msg="Privatekey must be a valid file with enough read permissions (%s)." % (privatekey))

    if not os.path.isdir(project_dir):
        os.makedirs(project_dir)

    os.chdir(project_dir)
    returncode = subprocess.call(["git", "init"], stdout=subprocess.PIPE)
    if returncode > 0:
        module.fail_json(msg="Unable to create bare repository in directory (%s)." % (project_dir))

    if remote:
        ssh_dir = os.path.join(os.path.expanduser('~'), ".ssh")
        projkey = os.path.join(ssh_dir, project + '.privatekey')

        if privatekey and not os.path.exists(ssh_dir):
            os.makedirs(ssh_dir)
            os.chmod(ssh_dir, 0o700)

        if os.path.isfile(projkey):
            src = digest(privatekey)
            dest = digest(projkey)
            if src != dest:
                shutil.copyfile(privatekey, projkey)
        else:
            shutil.copyfile(privatekey, projkey)
        os.chmod(projkey, 0o400)

        user, host = remote.split('@')
        host, path = host.split(':')
        sshconfig = os.path.join(ssh_dir, 'config')
        if not string_in_file(sshconfig, host):
            make_sshcfg(sshconfig, host, user, projkey)

        noerror = subprocess.call(["git", "remote", "rm", "origin"], stdout=subprocess.PIPE)
        returncode = subprocess.call(["git", "remote", "add", "origin", remote], stdout=subprocess.PIPE)
        if returncode > 0:
            module.fail_json(msg="Unable to add remote repository (%s) to the existing git project (%s)." % (remote, project_dir))

    module.exit_json(changed=True, rootdir=rootdir, project=project, remote=remote, privatekey=privatekey)

# import module snippets
from ansible.module_utils.basic import *
if __name__ == '__main__':
    main()

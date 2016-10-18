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
module: hammer
short_description: Deploy a package to a Satellite 6 repository.
description:
   - Deploy a given RPM to a Satellite 6 repository using Hammer commands.
version_added: "1.0"
author: "Joao Grilo (@jmgnm) <joao.grilo@gmail.com>"
'''

EXAMPLES = '''
# Publish an rpm package in a composite content view
- hammer: username=admin password=secret organization="ingdirect" product="f2e" name="f2e" content_view="RHEL6" lifecycle_environment="F2E server des" composite_view=True
'''


import os


class Hammer:

	def __init__(self, module, username, password, organization):
		self.module = module
		self.username = username
		self.password = password
		self.organization = organization

	def _cmd(self, args, check_rc=False):
		rc, out, err = self.module.run_command(command, check_rc)
		return (rc, out, err)

	def _hammer(self, args):
		command = 'hammer -u %s -p %s --output=yaml ' % (self.username, self.password)
		command += args
		command += ' --organization %s' % self.organization
		return self._cmd(command)

	def upload_content(rpm_path, name, product):
		args = 'repository upload-content --path %s --name %s --product %s' % (rpm_path, organization, name, product)
		rc, out, err = self._hammer(args)
		return out

	def publish(content_view):
		args = 'content-view publish --name %s' % (content_view)
		rc, out, err = self._hammer(args)
		return out

	def version_list(content_view):
		args = 'content-view version list --name %s' % (content_view)
		rc, out, err = self._hammer(args)
		return out

	def info(content_view):
		args = 'content-view info --name %s' % (content_view)
		rc, out, err = self._hammer(args)
		return out

	def update(content_view, components):
		args = 'content-view update --name %s --component-ids %s' % (content_view, ",".join(components))
		rc, out, err = self._hammer(args)
		return out

	def promote(id, lifecycle_environment):
		args = 'content-view version promote --id %s --to-lifecycle-environment "%s"' % (id, lifecycle_environment)
		rc, out, err = self._hammer(args)
		return out


def main():
    module = AnsibleModule(
        argument_spec=dict(
            username=dict(required=True),
            password=dict(required=True),
            rpm=dict(required=True, type='path'),
            organization=dict(required=True),
			product=dict(required=True),
			name=dict(required=True),
            content_view=dict(required=True),
			composite_view=dict(required=False, type='bool', default=False),
			lifecycle_environment=dict(required=False),
        ),
        supports_check_mode=False
    )

    username = module.params['username']
    password = module.params['password']
    organization = module.params['organization']
    rpm = module.params['rpm']
    product = module.params['product']
    name = module.params['name']
    content_view = module.params['content_view']
    composite_view = module.params['composite_view']
    lifecycle_environment = module.params['lifecycle_environment']

    # If the password is a file, read it
    if os.path.isfile(password):
        with open(password) as password_file:
            password = password_file.read().strip()

    if not os.path.isfile(rpm):
        module.fail_json(msg="rpm parameter (%s) must be a valid rpm file." % (rpm))

    cli = Hammer(module, username, password, organization)
    cli.upload_content(rpm, name, product)
    cli.publish(content_view)

    if composite_view:
        latest_id = cli.version_list(content_view)[-1]
        content_view_list = cli.info(composite_view)
        for cv in content_view_list:
            cli.update(cv, latest_id)
            cli.publish(composite_view)
        cli.promote(latest_id, lifecycle_environment)

    module.exit_json(changed=True, rpm_path=rpm_path, content_view=content_view)
 
from ansible.module_utils.basic import *
main()

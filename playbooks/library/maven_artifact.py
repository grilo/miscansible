#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2014, Chris Schmidt <chris.schmidt () contrastsecurity.com>
#
# Built using https://github.com/hamnis/useful-scripts/blob/master/python/download-maven-artifact
# as a reference and starting point.
#
# This module is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this software.  If not, see <http://www.gnu.org/licenses/>.

__author__ = 'cschmidt'

DOCUMENTATION = '''
---
module: maven_artifact
short_description: Downloads an Artifact from a Maven Repository
version_added: "2.0"
description:
    - Downloads an artifact from a maven repository given the maven coordinates provided to the module. Can retrieve
    - snapshots or release versions of the artifact and will resolve the latest available version if one is not
    - available.
author: "Chris Schmidt (@chrisisbeef)"
requirements:
    - "python >= 2.6"
    - lxml
options:
    group_id:
        description:
            - The Maven groupId coordinate
        required: true
    artifact_id:
        description:
            - The maven artifactId coordinate
        required: true
    version:
        description:
            - The maven version coordinate
        required: false
        default: latest
    classifier:
        description:
            - The maven classifier coordinate
        required: false
        default: null
    extension:
        description:
            - The maven type/extension coordinate
        required: false
        default: jar
    url_repository:
        aliases: [ repository_url, repository ]
        description:
            - The URL of the Maven Repository to download from
        required: false
        default: http://repo1.maven.org/maven2
    url_username:
        aliases: [ username, user, uname ]
        description:
            - The username to authenticate as to the Maven Repository
        required: false
        default: null
    url_password:
        aliases: [ password, pwd, passwd ]
        description:
            - The password to authenticate with to the Maven Repository
        required: false
        default: null
    dest:
        description:
            - The path where the artifact should be written to
        required: true
        default: false
    state:
        description:
            - The desired state of the artifact
        required: true
        default: present
        choices: [present,absent]
    validate_certs:
        description:
            - If C(no), SSL certificates will not be validated. This should only be set to C(no) when no other option exists.
        required: false
        default: 'yes'
        choices: ['yes', 'no']
        version_added: "1.9.3"
    ignore_checksum:
        description:
            - If C(yes), the checksum verification after downloading will be ignored. May result in corrupt artifacts if the network connection fails, but enables downloading artifacts which don't have a remote checksum calculated.
        required: false
        default: 'no'
        choices: ['yes', 'no']
        version_added: "2.1.0"
'''

EXAMPLES = '''
# Download the latest version of the JUnit framework artifact from Maven Central
- maven_artifact: group_id=junit artifact_id=junit dest=/tmp/junit-latest.jar
# Download JUnit 4.11 from Maven Central
- maven_artifact: group_id=junit artifact_id=junit version=4.11 dest=/tmp/junit-4.11.jar
# Download an artifact from a private repository requiring authentication
- maven_artifact: group_id=com.company artifact_id=library-name repository_url=https://repo.company.com/maven username=user password=pass dest=/tmp/library-name-latest.jar
# Download a WAR File to the Tomcat webapps directory to be deployed
- maven_artifact: group_id=com.company artifact_id=web-app extension=war repository_url=https://repo.company.com/maven dest=/var/lib/tomcat7/webapps/web-app.war
'''

from ansible.module_utils.basic import *
from ansible.module_utils.urls import *

import lxml.etree as etree
import os
import hashlib
import sys
import posixpath


class Artifact(object):
    def __init__(self, group_id, artifact_id, version, classifier=None, extension='jar'):
        self.group_id = group_id
        self.artifact_id = artifact_id
        self.version = version
        self.classifier = classifier
        self.extension = extension

    @property
    def url(self):
        return posixpath.join(self.group_id.replace(".", "/"), self.artifact_id, self.version, self.filename)

    @property
    def filename(self):
        bits = [self.artifact_id, self.version]
        if self.classifier:
            bits.append(self.classifier)
        return "-".join(bits) + "." + self.extension


class MavenClient:
    def __init__(self, module, repository):
        self.module = module
        self.repo = repository.rstrip("/")

    def get(self, url):
        url = posixpath.join(self.repo, url)
        response, info = fetch_url(self.module, url)
        if info['status'] != 200:
            raise Exception("Unable to complete request (%s)" % (url))
        return response.read()

    def download_metadata(self, artifact):
        url = "%s/maven-metadata.xml" % (posixpath.join(*artifact.url.split("/")[0:-2]))
        response = self.get(url)
        return etree.fromstring(response)

    def get_versions(self, artifact):
        # We are trusting the order returned by the XML, but should we?
        return self.download_metadata(artifact).xpath("/metadata/versioning/versions/version/text()")

    def get_md5(self, artifact):
        return self.get(artifact.url + '.md5')

    def download(self, artifact, destination):
        if os.path.isdir(destination) or destination.endswith("/"):
            destination = os.path.join(destination, artifact.filename)
        with open(destination, 'w') as file:
            response = self.get(artifact.url)
            file.write(response)
        return destination

    def checksum(self, artifact, dest):
        if not os.path.isfile(dest):
            return False
        remote_md5 = self.get_md5(artifact)
        local_md5 = None
        with open(dest, 'rb') as file:
            local_md5 = hashlib.md5(file.read()).hexdigest()

        return remote_md5 == local_md5


def main():

    module = AnsibleModule(
        argument_spec = dict(
            group_id = dict(required=True),
            artifact_id = dict(required=True),
            version = dict(default='latest'),
            classifier = dict(default=None),
            extension = dict(default='jar'),
            url_repository = dict(default='http://repo1.maven.org/maven2', aliases=['repository_url', 'repository']),
            url_username = dict(default=None, aliases=['username', 'user', 'uname']),
            url_password = dict(default=None, aliases=['password', 'pwd', 'passwd'], no_log=True),
            http_agent = dict(default='Maven Artifact Downloader/1.0'),
            state = dict(default='present', choices=['present','absent']),
            dest = dict(type='path', default=None),
            validate_certs = dict(default=True, type='bool'),
            ignore_checksum = dict(default=False, type='bool'),
        )
    )
    group_id = module.params["group_id"]
    artifact_id = module.params["artifact_id"]
    version = module.params["version"]
    classifier = module.params["classifier"]
    extension = module.params["extension"]
    repo = module.params["url_repository"]
    state = module.params["state"]
    dest = module.params["dest"]
    ignore_checksum = module.params["ignore_checksum"]

    client = MavenClient(module, repo)
    artifact = Artifact(group_id, artifact_id, version, classifier, extension)

    if version == 'latest':
        try:
            artifact.version = client.get_versions(artifact)[-1]
        except Exception, e:
            module.fail_json(msg=e.args[0])

    if os.path.isdir(dest):
        dest = os.path.join(dest, artifact.filename)

    # Should we delete the file?
    if state == 'absent':
        if os.path.isfile(dest):
            os.remove(dest)
            module.exit_json(dest=dest, state=state, changed=True)
        else:
            module.exit_json(dest=dest, state=state, changed=False)

    # Does the local file already exist and match the remote md5?
    if client.checksum(artifact, dest):
        module.exit_json(dest=dest, state=state, version=artifact.version, changed=False)

    try:
        client.download(artifact, dest)
    except Exception, e:
        module.fail_json(msg=e.args[0])

    if ignore_checksum and not client.checksum(artifact, dest):
        module.fail_json(msg="I was able to download the artifact (%s), but the checksum doesn't match (%s)." % (artifact.url, dest))

    module.exit_json(state=state, dest=dest, group_id=group_id, artifact_id=artifact_id, version=artifact.version, classifier=classifier, extension=extension, url_repository=repo, ignore_checksum=ignore_checksum, changed=True)


if __name__ == '__main__':
    main()

#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import json


def main():

    module = AnsibleModule(
        argument_spec = dict(
            link = dict(type="path", default=None),
            step = dict(type="int", required=False, default=1),
            force = dict(type="bool", required=False, default=False),
            sort = dict(required=False, default="name"),
        )
    )

    link = module.params["link"]
    step = module.params["step"]
    force = module.params["force"]
    sort = module.params["sort"]

    # Sanity check
    if not os.path.islink(link):
        module.fail_json(msg="Link parameter (%s) must be a valid symbolic link." % (link))
    if step == 0:
        module.fail_json(msg="The step parameter must be different than 0.")
    if sort not in ('name', 'creation', 'modification'):
        module.fail_json(msg="The sort parameter must be 'name', 'creation' or 'modification'")

    target = os.path.realpath(link)
    root_dir = os.path.dirname(target)
    symlink = os.path.basename(link)

    # Default to python's own sort if no known options are specified
    if sort == "creation":
        strategy = lambda x: os.stat(os.path.join(root_dir, x)).st_ctime
    elif sort == "modification":
        strategy = lambda x: os.stat(os.path.join(root_dir, x)).st_mtime
    else:
        strategy = None

    # Executing os.path.islink above already guarantees we can read the
    # contents of the directory, so no need for extra error checking
    contents = sorted(os.listdir(root_dir), key=strategy)
    contents.remove(symlink)

    delta = step + contents.index(os.path.basename(target))

    # If out of bounds and force is true, coalesce the delta to a sane value
    error = None
    if delta > len(contents) - 1:
        error = "Unable to move forward, invalid target. Delta: %d" % delta
        delta = -1
    elif delta < 0:
        error = "Unable to move backward, invalid target. Delta: %d" % delta
        delta = 0

    if error and not force:
        module.fail_json(msg=error + " Current: (%s) List: (%s)" % (os.path.basename(target), contents))

    new_link = os.path.join(root_dir, contents[delta])
    try:
        os.unlink(link)
        os.symlink(new_link, link)
    except OSError as e:
        module.fail_json(msg="Unable to change symlink from (%s) to (%s). Error: %s" % (new_link, link, e))

    module.exit_json(changed=True, old_link=link, new_link=new_link, final_index=delta)


# import module snippets
from ansible.module_utils.basic import *
if __name__ == '__main__':
    main()

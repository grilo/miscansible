#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import json
import shutil


def list_dirs(root_dir):
    dir_list = []
    for f in os.listdir(root_dir):
        f = os.path.join(root_dir, f)
        if os.path.isdir(f) and not os.path.islink(f):
            dir_list.append(f)
    return dir_list

def sort_dirs(sort, dir_list):
    # Default to python's own sort if no known options are specified
    if sort == "creation":
        strategy = lambda d: os.stat(d).st_ctime
    elif sort == "modification":
        strategy = lambda d: os.stat(d).st_mtime
    else:
        strategy = None
    return sorted(dir_list, key=strategy)

def main():

    module = AnsibleModule(
        argument_spec = dict(
            link = dict(type="path", default=None),
            step = dict(type="int", required=False, default=1),
            sort = dict(required=False, default="name"),
            prune = dict(type="bool", required=False, default=False),
        )
    )

    link = module.params["link"]
    step = module.params["step"]
    sort = module.params["sort"]
    prune = module.params["prune"]

    # Sanity check
    if not os.path.islink(link):
        module.fail_json(msg="Link parameter (%s) must be a valid symbolic link." % (link))
    if step == 0:
        module.fail_json(msg="The step parameter must be different than 0.")
    if sort not in ('name', 'creation', 'modification'):
        module.fail_json(msg="The sort parameter must be 'name', 'creation' or 'modification'")

    # Define our variables
    target = os.path.realpath(link)
    root_dir = os.path.dirname(target)
    symlink = os.path.basename(link)
    dir_list = sort_dirs(sort, list_dirs(root_dir))

    # If out of bounds, coalesce the index to a sane value
    index = step + dir_list.index(target)
    if index > len(dir_list) - 1:
        index = len(dir_list) - 1
    elif index < 0:
        index = 0

    # Relink
    new_link = dir_list[index]
    try:
        os.unlink(link)
        os.symlink(new_link, link)
    except OSError as e:
        module.fail_json(msg="Unable to change symlink from (%s) to (%s). Error: %s" % (new_link, link, e))

    if not prune:
        module.exit_json(changed=True, old_link=link, new_link=new_link, final_index=index)

    prune_dirs = []

    if step > 0:
        prune_dirs = dir_list[:index]
    elif step < 0:
        prune_dirs = dir_list[index+ 1:]

    for directory in prune_dirs:
        shutil.rmtree(directory)

    module.exit_json(changed=True, old_link=link, new_link=new_link, final_index=index, deleted=prune_dirs)

# import module snippets
from ansible.module_utils.basic import *
if __name__ == '__main__':
    main()

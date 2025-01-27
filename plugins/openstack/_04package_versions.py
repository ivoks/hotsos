#!/usr/bin/python3
import re

from common import (
    helpers,
    plugin_yaml,
)

from openstack_common import OST_PROJECTS, OST_DEP_PKGS

DEP_LIST = OST_PROJECTS + OST_DEP_PKGS
PKG_INFO = []


def get_pkg_info():
    dpkg_l = helpers.get_dpkg_l()
    if not dpkg_l:
        return

    for line in dpkg_l:
        for dep in DEP_LIST:
            ret = re.compile(r"^ii\s+(python3?-)?({}[0-9a-z\-]*)\s+(\S+)\s+.+"
                             .format(dep)).match(line)
            if ret:
                pyprefix = ret[1] or ""
                PKG_INFO.append("{}{} {}".format(pyprefix, ret[2], ret[3]))


if __name__ == "__main__":
    get_pkg_info()
    if PKG_INFO:
        PKG_INFO = {"dpkg": PKG_INFO}
        plugin_yaml.dump(PKG_INFO)

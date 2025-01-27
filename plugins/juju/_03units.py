#!/usr/bin/python3
import re
import os

from common import (
    helpers,
    plugin_yaml,
)
from juju_common import (
    JUJU_LOG_PATH
)

JUJU_UNIT_INFO = {"units": {}}


def get_app_from_unit(unit):
    ret = re.compile(r"([0-9a-z\-]+)-[0-9]+.*").match(unit)
    if ret:
        return ret[1]


def get_unit_version(unit):
    ret = re.compile(r"[0-9a-z\-]+-([0-9]+).*").match(unit)
    if ret:
        return int(ret[1])


def get_unit_info():
    unit_nonlocal = set()
    app_nonlocal = {}
    ps_units = set()
    log_units = set()
    app_local = set()
    units_local = set()
    units_local_not_running = set()
    units_local_not_running_filtered = set()
    units_nonlocal_dedup = set()

    if not os.path.exists(JUJU_LOG_PATH):
        return

    for line in helpers.get_ps():
        if "unit-" in line:
            ret = re.compile(r".+unit-([0-9a-z\-]+-[0-9]+).*").match(line)
            if ret:
                ps_units.add(ret[1])

    for f in os.listdir(JUJU_LOG_PATH):
        ret = re.compile(r"unit-(.+)\.log$").match(f)
        if ret:
            log_units.add(ret[1])

    combined_units = ps_units.union(log_units)

    for unit in combined_units:
        if unit in log_units:
            if unit in ps_units:
                app_local.add(unit.partition('-')[2])
                units_local.add(unit)
            else:
                units_local_not_running.add(unit)
        else:
            # i.e. it is running but there is no log file in /var/log/juju so
            # it is likely running in a container
            app = get_app_from_unit(unit)
            if app:
                version = get_unit_version(unit)
                if version is not None:
                    if app in app_nonlocal:
                        if version > app_nonlocal[app]:
                            app_nonlocal[app] = version
                    else:
                        app_nonlocal[app] = version

            unit_nonlocal.add(unit)

    # remove units from units_local_not_running that are just old versions of
    # the one currently running
    for unit in units_local_not_running:
        app = get_app_from_unit(unit)
        if not app or app not in app_local:
            units_local_not_running_filtered.add(unit)

    # dedup unit_nonlocal
    for unit in unit_nonlocal:
        app = get_app_from_unit(unit)
        version = app_nonlocal[app]
        if version == get_unit_version(unit):
            units_nonlocal_dedup.add(unit)

    if units_local:
        JUJU_UNIT_INFO["units"]["local"] = list(sorted(units_local))

    if units_local_not_running_filtered:
        JUJU_UNIT_INFO["units"]["stopped"] = \
            list(sorted(units_local_not_running_filtered))

    if units_nonlocal_dedup:
        JUJU_UNIT_INFO["units"]["lxd"] = \
            list(sorted(units_nonlocal_dedup))


if __name__ == "__main__":
    get_unit_info()
    if JUJU_UNIT_INFO:
        plugin_yaml.dump(JUJU_UNIT_INFO)

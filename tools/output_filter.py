#!/usr/bin/python3
import yaml

from common import (
    constants,
    issues_utils,
    known_bugs_utils,
    plugin_yaml,
)

FILTER_SCHEMA = [issues_utils.MASTER_YAML_ISSUES_FOUND_KEY,
                 known_bugs_utils.MASTER_YAML_KNOWN_BUGS_KEY]


def filter_master_yaml():
    with open(constants.MASTER_YAML_OUT) as fd:
        master_yaml = yaml.safe_load(fd)

    # Create a master list of issues and bugs adding info about which plugin
    # added them.

    filtered = {}
    for plugin in master_yaml:
        for key in FILTER_SCHEMA:
            if key in master_yaml[plugin]:
                if key not in filtered:
                    filtered[key] = {}

                items = master_yaml[plugin][key]
                for item in items:
                    for _key in item:
                        plug_key = "({}) {}".format(plugin, _key)
                        filtered[key][plug_key] = item[_key]

    with open(constants.MASTER_YAML_OUT, 'w') as fd:
        if filtered:
            fd.write(plugin_yaml.dump(filtered, ensure_master_has_plugin=False,
                                      stdout=False))
            fd.write("\n")
        else:
            fd.write("")


if __name__ == "__main__":
    filter_master_yaml()

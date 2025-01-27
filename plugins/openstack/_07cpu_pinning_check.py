#!/usr/bin/python3
import re
import os

from uuid import uuid4

from common import (
    constants,
    helpers,
    plugin_yaml,
)
from common.known_bugs_utils import add_known_bug
from openstack_common import (
    OPENSTACK_SHOW_CPU_PINNING_RESULTS,
)

CPU_PINNING_INFO = {}


def cores_to_list(cores):
    """Parse comma-seperated list of core ids into an array. Ranges are
    expanded.
    """
    total = []
    cores = cores.split(',')
    for subcores in cores:
        # expand ranges
        subcores = subcores.partition('-')
        if subcores[1] == '-':
            total += range(int(subcores[0]), int(subcores[2]) + 1)
        else:
            total.append(int(subcores[0]))

    return total


def squash_int_range(ilist):
    """Takes a list of integers and squashes consecutive values into a string
    range. Returned list contains mix of strings and ints.
    """
    irange = []
    rstart = None
    rprev = None

    sorted(ilist)
    for i, value in enumerate(ilist):
        if rstart is None:
            if i == (len(ilist) - 1):
                irange.append(value)
                break

            rstart = value

        if rprev is not None:
            if rprev != (value - 1):
                if rstart == rprev:
                    irange.append(rstart)
                else:
                    irange.append("{}-{}".format(rstart, rprev))
                    if i == (len(ilist) - 1):
                        irange.append(value)

                rstart = value
            elif i == (len(ilist) - 1):
                irange.append("{}-{}".format(rstart, value))
                break

        rprev = value

    return irange


def list_to_str(slist, seperator=None):
    """Convert list of any type to string seperated by seperator."""
    if not seperator:
        seperator = ','

    if not slist:
        return ""

    slist = squash_int_range(slist)

    return seperator.join([str(e) for e in slist])


class OpenstackNovaConfig(object):
    """Openstack Nova service configuration."""

    nova_config = []

    def __init__(self):
        path = os.path.join(constants.DATA_ROOT, "etc/nova/nova.conf")
        if os.path.exists(path):
            self.nova_config = open(path, 'r').readlines()

        self._cpu_dedicated_set = []
        self._cpu_shared_set = []
        self._vcpu_pin_set = []

    @property
    def cpu_dedicated_set(self):
        if self._cpu_dedicated_set:
            return self._cpu_dedicated_set

        for line in self.nova_config:
            expr = r'^cpu_dedicated_set\s*=\s*([0-9\-,]+)'
            ret = re.compile(expr).match(line)
            if ret:
                self._cpu_dedicated_set = cores_to_list(ret[1])
                break

        return self._cpu_dedicated_set

    @property
    def cpu_shared_set(self):
        if self._cpu_shared_set:
            return self._cpu_shared_set

        for line in self.nova_config:
            expr = r'^cpu_shared_set\s*=\s*([0-9\-,]+)'
            ret = re.compile(expr).match(line)
            if ret:
                self._cpu_shared_set = cores_to_list(ret[1])
                break

        return self._cpu_shared_set

    @property
    def vcpu_pin_set(self):
        if self._vcpu_pin_set:
            return self._vcpu_pin_set

        for line in self.nova_config:
            expr = r'^vcpu_pin_set\s*=\s*([0-9\-,]+)'
            ret = re.compile(expr).match(line)
            if ret:
                self._vcpu_pin_set = cores_to_list(ret[1])
                break

        return self._vcpu_pin_set


class KernelConfig(object):
    """ Kernel configuration. """

    kernel_config = []

    def __init__(self):
        path = os.path.join(constants.DATA_ROOT, "proc/cmdline")
        if os.path.exists(path):
            self.kernel_config = open(path, 'r').readlines()

        self._isolcpus = []

    @property
    def isolcpus(self):
        if self._isolcpus:
            return self._isolcpus

        for line in self.kernel_config:
            expr = r'.*\s+isolcpus=([0-9\-,]+)\s*.*'
            ret = re.compile(expr).match(line)
            if ret:
                self._isolcpus = cores_to_list(ret[1])
                break

        return self._isolcpus


class SystemdConfig(object):
    """Systemd configuration."""

    systemd_config = []

    def __init__(self):
        path = os.path.join(constants.DATA_ROOT, "etc/systemd/system.conf")
        if os.path.exists(path):
            self.systemd_config = open(path, 'r').readlines()

        self._cpuaffinity = []

    @property
    def cpuaffinity(self):
        if self._cpuaffinity:
            return self._cpuaffinity

        for line in self.systemd_config:
            expr = r'^CPUAffinity\s*=\s*([0-9\-,]+)\s*.*'
            ret = re.compile(expr).match(line)
            if ret:
                self._cpuaffinity = cores_to_list(ret[1])
                break

        return self._cpuaffinity


class NUMAInfo(object):

    numactl = ""

    def __init__(self):
        try:
            self.numactl = helpers.get_numactl() or ""
        except OSError:
            self.numactl = ""

        self._nodes = {}

    @property
    def nodes(self):
        """Returns dictionary of numa nodes and their associated list of cpu
           cores.
        """
        if self._nodes:
            return self._nodes

        node_ids = []
        for line in self.numactl:
            expr = r'^available:\s+[0-9]+\s+nodes\s+\(([0-9\-]+)\)'
            ret = re.compile(expr).match(line)
            if ret:
                p = ret[1].partition('-')
                if p[1] == '-':
                    node_ids = range(int(p[0]), int(p[2]) + 1)
                else:
                    node_ids = [int(p[0])]

                break

        for node in node_ids:
            for line in self.numactl:
                expr = r'^node\s+{}\s+cpus:\s([0-9\s]+)'.format(node)
                ret = re.compile(expr).match(line)
                if ret:
                    self._nodes[node] = [int(e) for e in ret[1].split()]
                    break

        return self._nodes

    def cores(self, node=None):
        """Returns list of cores for a given numa node.

        If no node id is provided, all cores from all numa nodes are returned.
        """
        return self.nodes.get(node)


class Results(object):
    def __init__(self):
        self.config = {}
        self._results = {"INFO": {"label": "info", "main": {}, "extras": {}},
                         "WARNING": {"label": "warnings", "main": {},
                                     "extras": {}},
                         "ERROR": {"label": "errors", "main": {},
                                   "extras": {}}}

    def add_config(self, application, key, value):
        """Save service/application config. This servces as a record of what
        we have used as a data source to cross-reference settings.
        """
        if not value:
            return

        if application in self.config:
            self.config[application][key] = value
        else:
            self.config[application] = {key: value}

    def _add_msg(self, level, msg, extra=None):
        """Add message to be displayed"""
        key = str(uuid4())
        self._results[level]["main"][key] = msg
        if extra:
            self._results[level]["extras"][key] = extra

    def add_info(self, msg, extra=None):
        """Add message to be displayed as INFO"""
        self._add_msg("INFO", msg, extra)

    def add_warn(self, msg, extra=None):
        """Add message to be displayed as WARNING"""
        self._add_msg("WARNING", msg, extra)

    def add_error(self, msg, extra=None):
        """Add message to be displayed as ERROR"""
        self._add_msg("ERROR", msg, extra)

    @property
    def has_results(self):
        return any([e[1]["main"] for e in self._results.items()])

    def get(self):
        if not (self.config or self.has_results):
            return

        if self.config:
            CPU_PINNING_INFO["input"] = {}
            for app in self.config:
                CPU_PINNING_INFO["input"][app] = self.config[app]

        if self.has_results:
            CPU_PINNING_INFO["results"] = {}
            for level in self._results:
                if not self._results[level]["main"]:
                    continue

                label = self._results[level]["label"]
                if label not in CPU_PINNING_INFO["results"]:
                    CPU_PINNING_INFO["results"][label] = []

                for key in self._results[level]["main"]:
                    msg = self._results[level]["main"][key]
                    CPU_PINNING_INFO["results"][label].append(msg)
                    extras = self._results[level]["extras"].get(key)
                    if OPENSTACK_SHOW_CPU_PINNING_RESULTS and extras:
                        _extras = {"extra-info": extras.split('\n')}
                        CPU_PINNING_INFO["results"][label].append(_extras)


class CPUPinningChecker(object):

    def __init__(self):
        self.numa = NUMAInfo()
        self.systemd = SystemdConfig()
        self.kernel = KernelConfig()
        self.openstack = OpenstackNovaConfig()
        self.results = Results()
        self.cpu_dedicated_set = set()
        self.cpu_dedicated_set_name = ""

        # >= Train
        if self.openstack.cpu_dedicated_set:
            self.cpu_dedicated_set = set(self.openstack.cpu_dedicated_set)
            self.cpu_dedicated_set_name = "cpu_dedicated_set"
        elif self.openstack.vcpu_pin_set:
            self.cpu_dedicated_set = set(self.openstack.vcpu_pin_set)
            self.cpu_dedicated_set_name = "vcpu_pin_set"

        self.cpu_shared_set = set(self.openstack.cpu_shared_set)
        self.isolcpus = set(self.kernel.isolcpus)
        self.cpuaffinity = set(self.systemd.cpuaffinity)

        self.results.add_config("nova", "cpu_dedicated_set",
                                list_to_str(self.openstack.cpu_dedicated_set))

        self.results.add_config("nova", "vcpu_pin_set",
                                list_to_str(self.openstack.vcpu_pin_set))

        self.results.add_config("nova", "cpu_shared_set",
                                list_to_str(self.openstack.cpu_shared_set))

        self.results.add_config("kernel", "isolcpus",
                                list_to_str(self.isolcpus))
        self.results.add_config("systemd", "cpuaffinity",
                                list_to_str(self.cpuaffinity))

        for node in self.numa.nodes:
            self.results.add_config("numa", "node{}".format(node),
                                    list_to_str(self.numa.cores(node)))

    def run_cpu_pinning_checks(self):
        """Perform a set of checks on Nova cpu pinning configuration to ensure
        it is setup as expected.
        """

        if self.cpu_dedicated_set:
            intersect1 = self.cpu_dedicated_set.intersection(self.isolcpus)
            intersect2 = self.cpu_dedicated_set.intersection(self.cpuaffinity)
            if intersect1:
                if intersect2:
                    extra = ("intersection with isolcpus: {}\nintersection "
                             "with cpuaffinity: {}".format(intersect1,
                                                           intersect2))
                    msg = ("{} is a subset of both isolcpus AND "
                           "cpuaffinity".format(self.cpu_dedicated_set_name))
                    self.results.add_error(msg, extra)
            elif intersect2:
                if intersect1:
                    extra = ("intersection with isolcpus: {}\nintersection "
                             "with cpuaffinity: {}".format(intersect1,
                                                           intersect2))
                    msg = ("{} is a subset of both isolcpus AND "
                           "cpuaffinity".format(self.cpu_dedicated_set_name))
                    self.results.add_error(msg, extra)
            else:
                msg = ("{} is neither a subset of isolcpus nor cpuaffinity".
                       format(self.cpu_dedicated_set_name))
                self.results.add_error(msg)
                reason = "cpu pinning check: {}".format(msg)
                add_known_bug(1897275, description=reason)

        intersect = self.cpu_shared_set.intersection(self.kernel.isolcpus)
        if intersect:
            extra = "intersection: {}".format(list_to_str(intersect))
            self.results.add_error("cpu_shared_set contains cores from "
                                   "isolcpus", extra)

        intersect = self.cpu_dedicated_set.intersection(self.cpu_shared_set)
        if intersect:
            extra = "intersection: {}".format(list_to_str(intersect))
            self.results.add_error("cpu_shared_set and {} overlap".
                                   format(self.cpu_dedicated_set_name),
                                   extra)

        intersect = self.isolcpus.intersection(self.cpuaffinity)
        if intersect:
            extra = "intersection: {}".format(list_to_str(intersect))
            self.results.add_error("isolcpus and cpuaffinity overlap", extra)

        node_count = 0
        for node in self.numa.nodes:
            if self.cpu_dedicated_set.intersection(set(self.numa.cores(node))):
                node_count += 1

        if node_count > 1:
            extra = ""
            for node in self.numa.nodes:
                if extra:
                    extra += "\n"

                extra += "node{}: {}".format(node,
                                             list_to_str(
                                                 self.numa.cores(node)))

            extra += "\n{}: {}".format(self.cpu_dedicated_set_name,
                                       list_to_str(self.cpu_dedicated_set))

            self.results.add_info("{} has cores from > 1 numa node".
                                  format(self.cpu_dedicated_set_name), extra)

        if self.isolcpus or self.cpuaffinity:
            total_isolated = self.isolcpus.union(self.cpuaffinity)
            nonisolated = set(total_isolated).intersection()
            if len(nonisolated) <= 4:
                self.results.add_warn("Host has only {} cores unpinned. This "
                                      "might cause unintended performance "
                                      "problems".format(len(nonisolated)))

    def get_results(self):
        self.results.get()


if __name__ == "__main__":
    checker = CPUPinningChecker()
    checker.run_cpu_pinning_checks()
    checker.get_results()
    if CPU_PINNING_INFO:
        CPU_PINNING_INFO = {"cpu-pinning-checks": CPU_PINNING_INFO}
        plugin_yaml.dump(CPU_PINNING_INFO)

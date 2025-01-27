import os

import datetime
import mock
import tempfile

import utils

from common import searchtools

utils.add_sys_plugin_path("openstack")

from plugins.openstack import (  # noqa E402
    _01openstack,
    _02vm_info,
    _03nova_external_events,
    _04package_versions,
    _05network,
    _06service_features,
    _07cpu_pinning_check,
    _08agent_checks,
)


APT_UCA = """
# Ubuntu Cloud Archive
deb http://ubuntu-cloud.archive.canonical.com/ubuntu bionic-updates/{} main
"""

SVC_CONF = """
debug = True
"""

with open(os.path.join(os.environ['DATA_ROOT'],
                       "sos_commands/networking/ip_-s_-d_link")) as fd:
    IP_LINK_SHOW = fd.readlines()


def fake_ip_link_show_w_errors_drops():
    lines = ''.join(IP_LINK_SHOW).format(10000000, 100000000)
    return [line + '\n' for line in lines.split('\n')]


def fake_ip_link_show_no_errors_drops():
    lines = ''.join(IP_LINK_SHOW).format(0, 0)
    return [line + '\n' for line in lines.split('\n')]


class TestOpenstackPlugin01openstack(utils.BaseTestCase):

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    @mock.patch.object(_01openstack, "OPENSTACK_INFO", {})
    def test_get_service_info(self):
        result = {'services': ['beam.smp (1)',
                               'haproxy (1)',
                               'neutron-ovn-metadata-agent (3)',
                               'nova-api-metadata (5)',
                               'nova-compute (1)',
                               'qemu-system-x86_64 (1)']}
        _01openstack.get_openstack_service_checker()()
        self.assertEqual(_01openstack.OPENSTACK_INFO, result)

    @mock.patch.object(_01openstack, "OPENSTACK_INFO", {})
    def test_get_release_info(self):
        with tempfile.TemporaryDirectory() as dtmp:
            for rel in ["stein", "ussuri", "train"]:
                with open(os.path.join(dtmp,
                                       "cloud-archive-{}.list".format(rel)),
                          'w') as fd:
                    fd.write(APT_UCA.format(rel))

            with mock.patch.object(_01openstack, "APT_SOURCE_PATH", dtmp):
                _01openstack.get_release_info()
                self.assertEqual(_01openstack.OPENSTACK_INFO,
                                 {"release": "ussuri"})

    @mock.patch.object(_01openstack, "OPENSTACK_INFO", {})
    def test_get_debug_log_info(self):
        result = {'debug-logging-enabled': {'neutron': True, 'nova': True}}
        with tempfile.TemporaryDirectory() as dtmp:
            for svc in ["nova", "neutron"]:
                conf_path = "etc/{svc}/{svc}.conf".format(svc=svc)
                os.makedirs(os.path.dirname(os.path.join(dtmp, conf_path)))
                with open(os.path.join(dtmp, conf_path), 'w') as fd:
                    fd.write(SVC_CONF)

            with mock.patch.object(_01openstack.constants,
                                   "DATA_ROOT", dtmp):
                _01openstack.get_debug_log_info()
                self.assertEqual(_01openstack.OPENSTACK_INFO, result)


class TestOpenstackPlugin02vm_info(utils.BaseTestCase):

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    @mock.patch.object(_02vm_info, "VM_INFO", [])
    def test_get_vm_info(self):
        _02vm_info.get_vm_info()
        self.assertEquals(_02vm_info.VM_INFO,
                          ["09461f0b-297b-4ef5-9053-dd369c86b96b"])


class TestOpenstackPlugin03nova_external_events(utils.BaseTestCase):

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    @mock.patch.object(_03nova_external_events, "EXT_EVENT_INFO", {})
    def test_get_events(self):
        data_root = _03nova_external_events.constants.DATA_ROOT
        data_source = os.path.join(data_root, "var/log/nova")
        _03nova_external_events.get_events("network-vif-plugged", data_source)
        events = {'network-vif-plugged':
                  {"succeeded":
                   [{"instance": 'd2666e01-73c8-4a97-9c22-0c175659e6db',
                     "port": "f6f5e6c5-2fdd-4719-9489-ca385d7fa7a7"},
                    {"instance": 'd2666e01-73c8-4a97-9c22-0c175659e6db',
                     "port": "1824336a-4bc3-46bb-9c08-bc86b1d24226"}],
                   "failed": [
                       {"instance": '5b367a10-9e6a-4eb9-9c7d-891dab7e87fa',
                        "port": "9a3673bf-58ac-423a-869a-6c4ae801b57b"}]}}
        self.assertEquals(_03nova_external_events.EXT_EVENT_INFO, events)


class TestOpenstackPlugin04package_versions(utils.BaseTestCase):

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    @mock.patch.object(_04package_versions, "PKG_INFO", [])
    def test_get_pkg_info(self):
        expected = [
            'ceilometer-agent-compute 1:10.0.1-0ubuntu0.18.04.2~cloud0',
            'ceilometer-common 1:10.0.1-0ubuntu0.18.04.2~cloud0',
            'conntrack 1:1.4.3-3',
            'dnsmasq-base 2.79-1~cloud0',
            'dnsmasq-utils 2.79-1~cloud0',
            'haproxy 1.6.3-1ubuntu0.3',
            'keepalived 1:1.3.9-1ubuntu0.18.04.2~cloud1',
            'libc-bin 2.23-0ubuntu11.2',
            'libvirt-daemon 4.0.0-1ubuntu8.15~cloud0',
            'libvirt-daemon-driver-storage-rbd 4.0.0-1ubuntu8.15~cloud0',
            'libvirt-daemon-system 4.0.0-1ubuntu8.15~cloud0',
            'neutron-common 2:12.1.0-0ubuntu1~cloud0',
            'neutron-dhcp-agent 2:12.1.0-0ubuntu1~cloud0',
            'neutron-l3-agent 2:12.1.0-0ubuntu1~cloud0',
            'neutron-metadata-agent 2:12.1.0-0ubuntu1~cloud0',
            'neutron-openvswitch-agent 2:12.1.0-0ubuntu1~cloud0',
            'nova-api-metadata 2:17.0.12-0ubuntu1~cloud0',
            'nova-common 2:17.0.12-0ubuntu1~cloud0',
            'nova-compute 2:17.0.12-0ubuntu1~cloud0',
            'nova-compute-kvm 2:17.0.12-0ubuntu1~cloud0',
            'nova-compute-libvirt 2:17.0.12-0ubuntu1~cloud0',
            'openvswitch-switch 2.9.5-0ubuntu0.18.04.1~cloud0',
            'python-barbicanclient 4.6.0-0ubuntu1~cloud0',
            'python-ceilometer 1:10.0.1-0ubuntu0.18.04.2~cloud0',
            'python-ceilometerclient 2.9.0-0ubuntu1~cloud0',
            'python-cinderclient 1:3.5.0-0ubuntu1~cloud0',
            'python-designateclient 2.9.0-0ubuntu1~cloud0',
            'python-glanceclient 1:2.9.1-0ubuntu1~cloud0',
            'python-keystone 2:13.0.2-0ubuntu3~cloud0',
            'python-keystoneauth1 3.4.0-0ubuntu1~cloud0',
            'python-keystoneclient 1:3.15.0-0ubuntu1~cloud0',
            'python-keystonemiddleware 4.21.0-0ubuntu1~cloud0',
            'python-neutron 2:12.1.0-0ubuntu1~cloud0',
            'python-neutron-fwaas 1:12.0.1-0ubuntu1~cloud0',
            'python-neutron-lib 1.13.0-0ubuntu1~cloud0',
            'python-neutronclient 1:6.7.0-0ubuntu1~cloud0',
            'python-nova 2:17.0.12-0ubuntu1~cloud0',
            'python-novaclient 2:9.1.1-0ubuntu1~cloud0',
            'python-oslo.cache 1.28.0-0ubuntu1~cloud0',
            'python-oslo.concurrency 3.25.0-0ubuntu1~cloud0',
            'python-oslo.config 1:5.2.0-0ubuntu1~cloud0',
            'python-oslo.context 1:2.20.0-0ubuntu1~cloud0',
            'python-oslo.db 4.33.0-0ubuntu1~cloud0',
            'python-oslo.i18n 3.19.0-0ubuntu1~cloud0',
            'python-oslo.log 3.36.0-0ubuntu1~cloud0',
            'python-oslo.messaging 5.35.0-0ubuntu1~cloud0',
            'python-oslo.middleware 3.34.0-0ubuntu1~cloud0',
            'python-oslo.policy 1.33.1-0ubuntu2~cloud0',
            'python-oslo.privsep 1.27.0-0ubuntu3~cloud0',
            'python-oslo.reports 1.26.0-0ubuntu1~cloud0',
            'python-oslo.rootwrap 5.13.0-0ubuntu1~cloud0',
            'python-oslo.serialization 2.24.0-0ubuntu2~cloud0',
            'python-oslo.service 1.29.0-0ubuntu1~cloud0',
            'python-oslo.utils 3.35.0-0ubuntu1~cloud0',
            'python-oslo.versionedobjects 1.31.2-0ubuntu3~cloud0',
            'python-swiftclient 1:3.5.0-0ubuntu1~cloud0',
            'qemu-kvm 1:2.11+dfsg-1ubuntu7.23~cloud0']
        _04package_versions.get_pkg_info()
        self.assertEquals(_04package_versions.PKG_INFO, expected)


class TestOpenstackPlugin05network(utils.BaseTestCase):

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    @mock.patch.object(_05network.helpers, 'get_ip_link_show',
                       fake_ip_link_show_w_errors_drops)
    def test_get_port_stat_by_name(self):
        stats = _05network.get_port_stats(name="bond1")
        self.assertEqual(stats, {'dropped': '100000000 (8%)'})

    @mock.patch.object(_05network.helpers, 'get_ip_link_show',
                       fake_ip_link_show_no_errors_drops)
    def test_get_port_stat_by_name_no_problems(self):
        stats = _05network.get_port_stats(name="bond1")
        self.assertEqual(stats, {})

    @mock.patch.object(_05network.helpers, 'get_ip_link_show',
                       fake_ip_link_show_w_errors_drops)
    def test_get_port_stat_by_mac(self):
        stats = _05network.get_port_stats(mac="ac:1f:6b:9e:d8:44")
        self.assertEqual(stats, {'errors': '10000000 (5%)'})

    def test_find_interface_name_by_ip_address(self):
        addr = "10.10.101.33"
        name = _05network.find_interface_name_by_ip_address(addr)
        self.assertEqual(name, "br-bond1")

    @mock.patch.object(_05network, "NETWORK_INFO", {})
    def test_get_ns_info(self):
        ns_info = {'namespaces': {'qdhcp': 35, 'qrouter': 35, 'fip': 1}}
        _05network.get_ns_info()
        self.assertEqual(ns_info, _05network.NETWORK_INFO)

    @mock.patch.object(_05network.helpers, "get_ip_netns", lambda: [])
    def test_get_ns_info_none(self):
        ns_info = _05network.get_ns_info()
        self.assertEqual(ns_info, None)


class TestOpenstackPlugin06service_features(utils.BaseTestCase):

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    @mock.patch.object(_06service_features, "SERVICE_FEATURES", {})
    def test_get_service_features(self):
        _06service_features.get_service_features()
        expected = {'neutron': {'neutron': {'availability_zone': 'AZ1'}}}
        self.assertEqual(_06service_features.SERVICE_FEATURES, expected)


class TestOpenstackPlugin07cpu_pinning_check(utils.BaseTestCase):

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def test_cores_to_list(self):
        ret = _07cpu_pinning_check.cores_to_list("0-4,8,9,28-32")
        self.assertEqual(ret, [0, 1, 2, 3, 4, 8, 9, 28, 29, 30, 31, 32])


class TestOpenstackPlugin08agent_checks(utils.BaseTestCase):

    def setUp(self):
        super().setUp()

    def tearDown(self):
        super().tearDown()

    def test_process_rpc_loop_results(self):
        end = datetime.datetime(2021, 3, 2, 14, 26, 55, 682000)
        start = datetime.datetime(2021, 3, 2, 14, 26, 29, 780000)
        expected = {'rpc-loop': {"top": {1438: {'duration': 25.9,
                                                'end': end,
                                                'start': start}},
                                 "stats": {"min": 25.9,
                                           "max": 25.9,
                                           "stdev": 0.0,
                                           "avg": 25.9,
                                           "samples": 1}}}
        s = searchtools.FileSearcher()
        c = _08agent_checks.NeutronAgentChecks(s)
        c.add_rpc_loop_search_terms()
        c.process_rpc_loop_results(s.search())
        self.assertEqual(c.ovs_agent_info, expected)

    @mock.patch.object(_08agent_checks, "add_known_bug")
    def test_get_agents_issues(self, mock_add_known_bug):
        neutron_expected = {'neutron-openvswitch-agent':
                            {'MessagingTimeout': {'2021-03-04': 2},
                             'AMQP server on 10.10.123.22:5672 is unreachable':
                             {'2021-03-04': 3},
                             'OVS is dead': {'2021-03-29': 1},
                             'RuntimeError': {'2021-03-29': 3},
                             }}
        nova_expected = {'nova-api-wsgi':
                         {'OSError: Server unexpectedly closed connection':
                          {'2021-03-15': 1},
                          'AMQP server on 10.5.1.98:5672 is unreachable':
                          {'2021-03-15': 1},
                          'amqp.exceptions.ConnectionForced':
                          {'2021-03-15': 1}},
                         'nova-compute':
                         {'DBConnectionError': {'2021-03-08': 2}}}
        s = searchtools.FileSearcher()
        c = _08agent_checks.CommonAgentChecks(s)
        c.add_agents_issues_search_terms()
        c.process_agent_issues_results(s.search())
        self.assertEqual(c.agent_log_issues,
                         {"neutron": neutron_expected, "nova": nova_expected})
        calls = [mock.call("1896506",
                           description=('identified in neutron-l3-agent logs '
                                        'by testplugin.01part'))]
        mock_add_known_bug.assert_has_calls(calls)

    def test_get_router_event_stats(self):
        router = '9b8efc4c-305b-48ce-a5bd-624bc5eeee67'
        spawn_start = datetime.datetime(2021, 3, 25, 18, 10, 14, 747000)
        spawn_end = datetime.datetime(2021, 3, 25, 18, 10, 50, 838000)
        update_start = datetime.datetime(2021, 3, 25, 18, 9, 54, 720000)
        update_end = datetime.datetime(2021, 3, 25, 18, 10, 36, 942000)
        expected = {'router-spawn-events': {'stats': {'avg': 36.09,
                                                      'max': 36.09,
                                                      'min': 36.09,
                                                      'samples': 1,
                                                      'stdev': 0.0},
                                            'top': {router:
                                                    {'duration': 36.091,
                                                     'end': spawn_end,
                                                     'start': spawn_start}}},
                    'router-updates': {'stats': {'avg': 28.14,
                                                 'max': 42.22,
                                                 'min': 14.07,
                                                 'samples': 2,
                                                 'stdev': 14.08},
                                       'top': {router:
                                               {'duration': 42.222,
                                                'end': update_end,
                                                'start': update_start}}}}

        s = searchtools.FileSearcher()
        c = _08agent_checks.NeutronAgentChecks(s)
        c.add_router_event_search_terms()
        c.process_router_event_results(s.search())
        self.assertEqual(c.l3_agent_info, expected)

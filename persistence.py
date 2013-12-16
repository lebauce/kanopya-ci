import os
import time
import cPickle as pickle
import logging


logger = logging.getLogger(__name__)


class CIDB(object):
    """ simple pickle persistence with locking context capacity """
    def __init__(self, dbfile=os.path.join(os.path.dirname(__file__), 'cidb.pickled')):
        self._dbfile = dbfile
        self._lockfile = dbfile + '.lock'
        if os.path.exists(dbfile):
            self.load()
        else:
            logger.debug('no %s file, create one with default values',
                         self._dbfile)
            self.network = '10.0.3.0'
            self.ssh_port = 2222
            self.vrde_port = 3333
            self.vlan = 10
            self.jobs = {}
            self.physical_hosts = physical_hosts
            self.save()

    def __enter__(self):
        if os.path.exists(self._lockfile):
            logger.debug("%s already locked, waiting...", self._dbfile)
            while os.path.exists(self._lockfile):
                time.sleep(1)
        open(self._lockfile, 'w').close()
        return self

    def __exit__(self, type, value, traceback):
        if os.path.exists(self._lockfile):
            os.remove(self._lockfile)

    def __del__(self):
        if os.path.exists(self._lockfile):
            os.remove(self._lockfile)

    def load(self):
        logger.debug('loading db from %s', self._dbfile)
        with open(self._dbfile, 'r') as f:
            data = pickle.load(f)
        self.network = data['network']
        self.ssh_port = data['ssh_port']
        self.vrde_port = data['vrde_port']
        self.vlan = data['vlan']
        self.jobs = data['jobs']
        self.physical_hosts = data['physical_hosts']

    def save(self):
        data = {'network': self.network,
                'ssh_port': self.ssh_port,
                'vrde_port': self.vrde_port,
                'vlan': self.vlan,
                'jobs': self.jobs,
                'physical_hosts': self.physical_hosts}
        with open(self._dbfile, 'w') as f:
            pickle.dump(data, f)

    def dump(self):
        print
        print "last network: {0}".format(self.network)
        print "last ssh port: {0}".format(self.ssh_port)
        print "last vrde port: {0}".format(self.vrde_port)
        print "last vlan: {0}".format(self.vlan)
        print
        print "physical hosts :"
        for host in self.physical_hosts:
            print " {0}".format(host['serial_number']),
            if host['job'] is not None:
                print "({0})".format(host['job'])
            else:
                print
        print
        for job in self.jobs.keys():
            print "job: {0}".format(job)
            print "net: {0}".format(self.jobs[job]['net'])
            print "ssh port: {0}".format(self.jobs[job]['ssh_port'])
            print "vrde port: {0}".format(self.jobs[job]['vrde_port'])
            print "vlan: {0}".format(self.jobs[job]['vlan'])
            if self.jobs[job]['infra'] is not None:
                print "infra: {0}".format(
                    self.jobs[job]['infra'].__class__.__name__)
                print "{0}".format(self.jobs[job]['infra'])
            else:
                print "infra: None"
            print

    def new_network(self):
        """
        Generate a new network by using the last network and adding 1 to it
        For instance : 10.10.0.0 would give 10.10.1.0 and
        10.10.255.0 would give 10.11.0.0
        """
        previous = self.network
        network = previous.split(".")
        new_network = int(network[1]) * 256 + int(network[2]) + 1
        network = ".".join([network[0], str(new_network / 256),
                            str(new_network % 256), str(0)])
        ip = network.split('.')
        ip[3] = '2'
        ip = '.'.join(ip)
        self.network = network

        return (network, ip)

    def new_ssh_port(self):
        """ generate a new ssh port for nat forwarding """
        previous = self.ssh_port
        port = previous + 1
        self.ssh_port = port
        return port

    def new_vrde_port(self):
        """ generate a new vrde port for nat forwarding """
        previous = self.vrde_port
        port = previous + 1
        self.vrde_port = port
        return port

    def new_vlan(self):
        """ generate a new vlan """
        previous = self.vlan
        vlan = previous + 1
        self.vlan = vlan
        return vlan

    def get_vmname_from_mac(self, mac):
        """
        Return vm name which has an interface with the specified mac
        address.
        """
        for job in self.jobs.values():
            infra = job['infra']
            if infra is None:
                continue
            if not hasattr(infra, 'vms'):
                continue
            for vm in infra.vms:
                for iface in vm['ifaces']:
                    if iface['mac'] == mac:
                        return vm['serial_number']

        return None

    def get_available_hosts(self):
        """ return list of all free hosts """
        return [host for host in self.physical_hosts if host['job'] is None]


physical_hosts = [
    #{'serial_number': "Rochefort",
     #'job': None,
     #'ram': 17179869184,
     #'core': 8,
     #'tags': ['hypervisor'],
     #'ifaces': [{'name': "eth0",
                 #'mac': "54:04:a6:91:3e:d0",
                 #'pxe': 1,
                 #'switch_port': 10,
                 #'mb': 1},
                #{'name': "eth1",
                 #'mac': "68:05:ca:0a:71:cf",
                 #'pxe': 0,
                 #'switch_port': 11}],
     #'harddisks': [{'device': "/dev/sda", 'size': "858993459200"}]},
#
    #{'serial_number': "Bernardus",
     #'job': None,
     #'ram': 16737280000,
     #'core': 8,
     #'tags': ['hypervisor'],
     #'ifaces': [{'name': "eth0",
                 #'mac': "54:04:a6:ce:0d:8e",
                 #'pxe': 1,
                 #'switch_port': 12,
                 #'mb': 1},
                #{'name': "eth1",
                 #'mac': "a0:f3:c1:00:6e:4e",
                 #'pxe': 0,
                 #'switch_port': 13}],
     #'harddisks': []},
#
#    {'serial_number': "Westmalle",
#     'job': None,
#     'ram': 16737280000,
#     'core': 8,
#     'tags': ['hypervisor'],
#     'ifaces': [{'name': "eth0",
#                 'mac': "f8:d1:11:b5:4d:97",
#                 'pxe': 1,
#                 'switch_port': 14},
#                {'name': "eth1",
#                 'mac': "10:bf:48:76:57:47",
#                 'pxe': 0,
#                 'switch_port': 15,
#                 'mb': 1}],
#     'harddisks': [{'device': "/dev/sda", 'size': "214748364800"}]},

#    {'serial_number': "Bon Secours",
#     'job': None,
#     'ram': 16737280000,
#     'core': 8,
#     'tags': ['hypervisor'],
#     'ifaces': [{'name': "eth0",
#                 'mac': "f8:d1:11:c3:14:a0",
#                 'pxe': 1,
#                 'switch_port': 16},
#                {'name': "eth1",
#                 'mac': "30:85:a9:46:b5:8b",
#                 'pxe': 0,
#                 'switch_port': 17}],
#     'harddisks': [{'device': "/dev/sda", 'size': "214748364800"}]},

    #{'serial_number': "Chimay",
     #'job': None,
     #'ram': 4294967296,
     #'core': 4,
     #'tags': [],
     #'ifaces': [{'name': "eth0",
                 #'mac': "70:71:bc:6c:56:b7",
                 #'pxe': 1,
                 #'switch_port': 18}],
     #'harddisks': []},

    {'serial_number': "Supermicro Server",
     'job': None,
     'ram': 8589934592,
     'core': 4,
     'tags': ['hypervisor', 'ipmi'],
     'ifaces': [{'name': "eth1",
                 'mac': "00:25:90:a5:13:aa",
                 'pxe': 0,
                 'switch_port': 19},
                {'name': "eth0",
                 'mac': "00:25:90:a5:13:ab",
                 'pxe': 1 }],

     'harddisks': [{'device': "/dev/sda", 'size': "214748364800"}],
     'ipmicredentials': [{'ip_addr': "10.0.0.200", 
                         'user': "ADMIN", 
                         'password': "admin"}]},


#    {'serial_number': "Petrus",
#     'job': None,
#     'ram': 8589934592,
#     'core': 4,
#     'tags': ['hypervisor'],
#     'ifaces': [{'name': "eth0",
#                 'mac': "1c:6f:65:c5:66:50",
#                 'pxe': 1,
#                 'switch_port': 19}],
#     'harddisks': [{'device': "/dev/sda", 'size': "214748364800"}]},

    #{'serial_number': "Orval",
     #'job': None,
     #'ram': 8589934592,
     #'core': 8,
     #'tags': ['hypervisor'],
     #'blade': 1,
     #'ifaces': [{'name': "eth0",
                 #'mac': "00:25:90:a4:97:58",
                 #'pxe': 1,
                 #'switch_port': 20},
                #{'name': "eth1",
                 #'mac': "00:25:90:a4:97:59",
                 #'pxe': 0,
                 #'switch_port': 21}],
     #'harddisks': []},
#
    #{'serial_number': "Duvel",
     #'job': None,
     #'ram': 8589934592,
     #'core': 8,
     #'tags': ['hypervisor'],
     #'blade': 1,
     #'ifaces': [{'name': "eth0",
                 #'mac': "00:25:90:a5:13:aa",
                 #'pxe': 1,
                 #'switch_port': 22},
                #{'name': "eth1",
                 #'mac': "00:25:90:a5:13:ab",
                 #'pxe': 0,
                 #'switch_port': 23}],
     #'harddisks': []},

    #{'serial_number': "Maredsou",
     #'job': None,
     #'ram': 17179869184,
     #'core': 4,
     #'tags': ['hypervisor'],
     #'ifaces': [{'name': "eth0",
                 #'mac': "6c:62:6d:46:bb:45",
                 #'pxe': 1,
                 #'switch_port': 24},
                #{'name': "eth1",
                 #'mac': "00:50:ba:ea:84:78",
                 #'pxe': 0,
                 #'switch_port': 25}],
     #'harddisks': []},
#
    #{'serial_number': "Kwak",
     #'job': None,
     #'ram': 4294967296,
     #'core': 4,
     #'tags': ['hypervisor'],
     #'ifaces': [{'name': "eth0",
                 #'mac': "f8:d1:11:02:34:3e",
                 #'pxe': 1,
                 #'switch_port': 26},
                #{'name': "eth1",
                 #'mac': "8c:89:a5:15:9b:1c",
                 #'pxe': 0,
                 #'switch_port': 27}],
     #'harddisks': []}
]


if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG)
    with CIDB() as db:
        db.dump()
